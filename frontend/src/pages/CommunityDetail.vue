<template>
  <div class="community-detail-page" :style="{ marginTop: '70px', paddingTop: '20px' }">
    <div class="container">
      <el-button @click="$router.back()" type="info" plain>{{ t('back') }}</el-button>

      <div v-if="loading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon> {{ t('loading') }}
      </div>

      <div v-else-if="community" class="community-detail">
        <div class="community-header">
          <div>
            <h1>{{ localizeCommunityName(community.name, community.state, community.city) }}</h1>
            <p class="location">{{ localizeCommunityName(community.name, community.state, community.city) }} {{ community.zipcode }}</p>
          </div>
          <div class="header-actions">
            <button v-if="isLoggedIn" class="btn btn-primary" @click="toggleFollow">
              {{ isFollowing ? t('unfollow') : t('follow') }}
            </button>
            <button v-if="isLoggedIn" class="btn btn-primary" @click="exportReport">{{ t('exportReport') }}</button>
          </div>
        </div>

        <div class="safety-score">
          <div class="score-large">{{ community.safetyScore }}</div>
          <div class="score-info">
            <p class="score-level">{{ getSafetyLevelLabel(community.safetyLevel) }}</p>
            <p class="score-trend">
              {{ community.trend === 'up' ? t('trendUp') : community.trend === 'down' ? t('trendDown') : t('trendStable') }}
            </p>
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat">
            <div class="stat-label">{{ t('population') }}</div>
            <div class="stat-value">{{ formatNumber(community.population) }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('area') }}</div>
            <div class="stat-value">{{ community.area || '-' }} sq mi</div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('recentEvents30d') }}</div>
            <div class="stat-value">{{ totalRecentEvents }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">{{ t('topEventType') }}</div>
            <div class="stat-value">{{ topEventType }}</div>
          </div>
        </div>

        <div class="details-grid">
          <div class="map-section">
            <h3>{{ t('communityMap') }}</h3>
            <div id="community-map" class="community-map"></div>
            <p v-if="mapError" class="map-error">{{ mapError }}</p>
          </div>

          <div class="charts-section">
            <h3>{{ t('dataVisualization') }}</h3>
            <div id="event-type-chart" class="chart"></div>
            <div id="event-trend-chart" class="chart"></div>
          </div>
        </div>

        <div class="report-section">
          <h3>{{ t('communitySafetyReport') }}</h3>
          <div class="report-content">
            <div class="report-item">
              <h4>{{ t('highRiskTimePeriods') }}</h4>
              <p>{{ communityReport.highRiskPeriods }}</p>
            </div>
            <div class="report-item">
              <h4>{{ t('highRiskLocations') }}</h4>
              <p>{{ communityReport.highRiskLocations }}</p>
            </div>
            <div class="report-item">
              <h4>{{ t('safetyTips') }}</h4>
              <p>{{ communityReport.safetyTips }}</p>
            </div>
            <div class="report-item">
              <h4>{{ t('yearOverYearComparison') }}</h4>
              <p>{{ communityReport.yoyComparison }}</p>
            </div>
          </div>
        </div>

        <div class="recent-events">
          <h3>{{ t('recentEventsIn') }} {{ localizeCommunityName(community.name, community.state, community.city) }}</h3>
          <div v-if="recentEvents.length === 0" class="empty-state">
            <p>{{ t('noRecentEvents') }}</p>
          </div>
          <div v-else class="events-list">
            <div v-for="event in recentEvents" :key="event.id" class="event-row" @click="goToEvent(event.id)">
              <span class="event-type-badge" :style="{ backgroundColor: getEventColor(event.type) }">
                {{ getEventTypeLabel(event.type) }}
              </span>
              <span class="event-info">{{ event.title }} - {{ formatTime(event.eventTime) }}</span>
            </div>
          </div>
          <div v-if="totalRecentEventPages > 1" class="events-pagination">
            <el-pagination
              v-model:current-page="eventPage"
              v-model:page-size="eventPageSize"
              :total="totalRecentEvents"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="loadCommunityEvents"
              @size-change="onEventPageSizeChange"
            />
          </div>
          <router-link :to="`/events?community=${community.id}`" class="btn btn-secondary">{{ t('viewAllEvents') }}</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import L from 'leaflet'
import * as echarts from 'echarts'
import { useUserStore } from '../stores/app'
import { communityService, eventService } from '../services/api'
import { dateUtils, eventTypeColors, getEventTypeLabel, getSafetyLevelLabel, localizeCommunityName, mapNoDataLabel } from '../utils/helpers'
import { useI18n } from '../utils/i18n'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()

const community = ref(null)
const recentEvents = ref([])
const totalRecentEvents = ref(0)
const eventPage = ref(1)
const eventPageSize = ref(20)
const loading = ref(false)
const isFollowing = ref(false)
const mapError = ref('')
let map = null
let pieChart = null
let lineChart = null

const isLoggedIn = computed(() => userStore.isLoggedIn)
const formatTime = (date) => dateUtils.daysAgo(date)
const formatNumber = (num) => (typeof num === 'number' ? num.toLocaleString() : '-')
const getEventColor = (type) => eventTypeColors[type] || '#999'

const WORLD_BOUNDS = [
  [-85, -180],
  [85, 180],
]
const NORTH_AMERICA_VIEW = [45, -100]
const GEOJSON_CANDIDATE_PATHS = [
  `${import.meta.env.BASE_URL}countries.geojson`,
  '/countries.geojson',
  './countries.geojson',
]

const buildSeparatedEventPoints = (events = []) => {
  const cellSize = 0.06
  const grouped = new Map()
  const points = []

  events.forEach((event) => {
    const lat = Number(event.latitude)
    const lng = Number(event.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
    const cellKey = `${Math.round(lat / cellSize)}_${Math.round(lng / cellSize)}`
    const group = grouped.get(cellKey) || []
    const point = { event, lat, lng }
    group.push(point)
    grouped.set(cellKey, group)
    points.push(point)
  })

  grouped.forEach((group) => {
    if (group.length <= 1) return
    const centerLat = group.reduce((sum, p) => sum + p.lat, 0) / group.length
    const lngScale = Math.max(Math.cos((centerLat * Math.PI) / 180), 0.3)
    group.forEach((point, idx) => {
      const ringSize = 8
      const ring = Math.floor(idx / ringSize)
      const slot = idx % ringSize
      const angle = (((slot * 360) / ringSize + ring * 19) * Math.PI) / 180
      const radius = 0.035 + ring * 0.022
      point.lat += radius * Math.sin(angle)
      point.lng += (radius * Math.cos(angle)) / lngScale
    })
  })

  return points
}

const loadWorldGeojsonLayer = async (targetMap) => {
  for (const path of GEOJSON_CANDIDATE_PATHS) {
    try {
      const res = await fetch(path)
      if (!res.ok) continue
      const geojson = await res.json()
      L.geoJSON(geojson, {
        pane: 'basePane',
        style: {
          color: '#334155',
          weight: 0.8,
          fillColor: '#d4d7bd',
          fillOpacity: 0.82,
        },
      }).addTo(targetMap)
      return true
    } catch {
      // try next candidate
    }
  }
  return false
}

const normalizeCommunity = (item) => {
  if (!item) return null
  return {
    ...item,
    safetyScore: item.safety_score ?? item.safetyScore ?? 0,
    safetyLevel: item.safety_level ?? item.safetyLevel ?? 'medium',
    report: item.report ?? {
      highRiskPeriods: mapNoDataLabel(),
      highRiskLocations: mapNoDataLabel(),
      safetyTips: mapNoDataLabel(),
      yoyComparison: mapNoDataLabel(),
    },
  }
}

const topEventType = computed(() => {
  if (!recentEvents.value.length) return 'N/A'
  const counter = {}
  recentEvents.value.forEach((item) => {
    counter[item.type] = (counter[item.type] || 0) + 1
  })
  return getEventTypeLabel(Object.keys(counter).sort((a, b) => counter[b] - counter[a])[0])
})
const totalRecentEventPages = computed(() =>
  Math.max(1, Math.ceil((totalRecentEvents.value || 0) / (eventPageSize.value || 1)))
)

const communityReport = computed(() => {
  return (
    community.value?.report || {
      highRiskPeriods: mapNoDataLabel(),
      highRiskLocations: mapNoDataLabel(),
      safetyTips: mapNoDataLabel(),
      yoyComparison: mapNoDataLabel(),
    }
  )
})

const buildTrendData = () => {
  const bucket = {}
  recentEvents.value.forEach((item) => {
    const dateKey = new Date(item.eventTime).toISOString().slice(0, 10)
    bucket[dateKey] = (bucket[dateKey] || 0) + 1
  })
  const labels = Object.keys(bucket).sort()
  return {
    labels,
    values: labels.map((k) => bucket[k]),
  }
}

const initMap = async () => {
  const mapContainer = document.getElementById('community-map')
  if (!mapContainer || !community.value) return
  mapError.value = ''

  // Force container size in case layout has not stabilized yet.
  if (!mapContainer.style.height) {
    mapContainer.style.height = '340px'
  }
  if (!mapContainer.style.minHeight) {
    mapContainer.style.minHeight = '340px'
  }

  if (map) {
    map.remove()
    map = null
  }
  if (mapContainer._leaflet_id) {
    mapContainer._leaflet_id = null
  }

  try {
    map = L.map('community-map', {
      zoomControl: true,
      attributionControl: true,
    })
    map.createPane('basePane')
    map.getPane('basePane').style.zIndex = '350'
    map.createPane('eventPane')
    map.getPane('eventPane').style.zIndex = '640'
    map.createPane('communityPane')
    map.getPane('communityPane').style.zIndex = '680'

    map.setView(NORTH_AMERICA_VIEW, 3)
    map.setMinZoom(2)
    map.setMaxZoom(10)
    map.setMaxBounds(WORLD_BOUNDS)
    map.getContainer().style.background = '#a9d7f5'

    const hasWorldLayer = await loadWorldGeojsonLayer(map)
    if (!hasWorldLayer) {
      L.rectangle(WORLD_BOUNDS, {
        pane: 'basePane',
        color: '#475569',
        weight: 1,
        fillColor: '#d4d7bd',
        fillOpacity: 0.75,
      }).addTo(map)
      console.error('Failed to load geojson map in CommunityDetail')
    }

    const lat = Number(community.value.latitude)
    const lng = Number(community.value.longitude)
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      map.setView([lat, lng], 9)
      L.circleMarker([lat, lng], {
        pane: 'communityPane',
        radius: 9,
        fillColor: '#2563eb',
        color: '#0f172a',
        weight: 2,
        fillOpacity: 0.95,
      })
        .bindPopup(`${community.value.name} (Safety ${community.value.safetyScore})`)
        .addTo(map)
    }

    const separatedPoints = buildSeparatedEventPoints(recentEvents.value)
    separatedPoints.forEach(({ event, lat: eLat, lng: eLng }) => {
      L.circleMarker([eLat, eLng], {
        pane: 'eventPane',
        radius: 5,
        fillColor: getEventColor(event.type),
        color: '#111',
        weight: 1,
        fillOpacity: 0.85,
      })
        .bindPopup(`${event.title}<br>${getEventTypeLabel(event.type)}`)
        .addTo(map)
    })

    map.whenReady(() => {
      map.invalidateSize()
    })
    setTimeout(() => {
      if (map) map.invalidateSize()
    }, 120)
  } catch (error) {
    console.error('Failed to init community map', error)
    mapError.value = t('mapFailedToLoad')
  }
}

const initMapWithRetry = async () => {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await initMap()
    if (map || mapError.value) return
    await new Promise((resolve) => setTimeout(resolve, 120))
  }
}

const initCharts = () => {
  const pieEl = document.getElementById('event-type-chart')
  const lineEl = document.getElementById('event-trend-chart')
  if (!pieEl || !lineEl) return
  if (pieChart) {
    pieChart.dispose()
    pieChart = null
  }
  if (lineChart) {
    lineChart.dispose()
    lineChart = null
  }

  const typeCount = {}
  recentEvents.value.forEach((item) => {
    typeCount[item.type] = (typeCount[item.type] || 0) + 1
  })
  const pieData = Object.keys(typeCount).map((key) => ({
    name: getEventTypeLabel(key),
    value: typeCount[key],
  }))

  const trend = buildTrendData()

  pieChart = echarts.init(pieEl)
  pieChart.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: '65%',
        data: pieData.length ? pieData : [{ name: t('noData'), value: 1 }],
      },
    ],
  })

  lineChart = echarts.init(lineEl)
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: trend.labels.length ? trend.labels : [t('noData')] },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        smooth: true,
        data: trend.values.length ? trend.values : [0],
      },
    ],
  })
}

const loadCommunity = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const communityRes = await communityService.getCommunityById(id)
    community.value = normalizeCommunity(communityRes.data.community)
    isFollowing.value = !!community.value?.is_following

    await loadCommunityEvents()
  } catch (error) {
    ElMessage.error('Failed to load community details')
    console.error(error)
    community.value = null
    recentEvents.value = []
  } finally {
    loading.value = false
    await nextTick()
    if (community.value) {
      await initMapWithRetry()
      try {
        initCharts()
      } catch (error) {
        console.error('Failed to init charts', error)
      }
    }
  }
}

const loadCommunityEvents = async () => {
  if (!community.value?.id && !route.params.id) return
  try {
    const eventsRes = await eventService.getEvents({
      community: community.value?.id || route.params.id,
      page: eventPage.value,
      pageSize: eventPageSize.value,
      timeRange: 30,
      sortBy: 'publishTime',
    })
    recentEvents.value = eventsRes.data.events || []
    totalRecentEvents.value = eventsRes.data.total || 0
  } catch (eventsError) {
    console.error('Failed to load community events', eventsError)
    recentEvents.value = []
    totalRecentEvents.value = 0
  }
}

const onEventPageSizeChange = () => {
  eventPage.value = 1
  loadCommunityEvents()
}

const toggleFollow = async () => {
  try {
    if (isFollowing.value) {
      await communityService.unfollowCommunity(community.value.id)
      ElMessage.success(t('communityUnfollowed'))
    } else {
      await communityService.followCommunity(community.value.id)
      ElMessage.success(t('follow'))
    }
    isFollowing.value = !isFollowing.value
  } catch {
    ElMessage.error(t('actionFailed'))
  }
}

const exportReport = () => {
  if (!community.value) return
  const content = [
    `Community: ${community.value.name}`,
    `Location: ${community.value.city}, ${community.value.state} ${community.value.zipcode || ''}`,
    `Safety Score: ${community.value.safetyScore}`,
    `Safety Level: ${community.value.safetyLevel}`,
    `Recent Event Count: ${recentEvents.value.length}`,
    `Top Event Type: ${topEventType.value}`,
    '',
    `High-Risk Time Periods: ${communityReport.value.highRiskPeriods}`,
    `High-Risk Locations: ${communityReport.value.highRiskLocations}`,
    `Safety Tips: ${communityReport.value.safetyTips}`,
    `Year-over-Year: ${communityReport.value.yoyComparison}`,
  ].join('\n')
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `community-${community.value.id}-report.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const goToEvent = (id) => router.push(`/events/${id}`)

onMounted(loadCommunity)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
  if (pieChart) {
    pieChart.dispose()
    pieChart = null
  }
  if (lineChart) {
    lineChart.dispose()
    lineChart = null
  }
})
</script>

<style scoped>
.community-detail-page {
  background-color: var(--bg-color);
  min-height: calc(100vh - 70px);
  padding-bottom: 40px;
}

.dark-mode .community-detail-page {
  background-color: transparent;
}

.community-header,
.safety-score,
.stat,
.map-section,
.charts-section,
.report-section,
.recent-events {
  background-color: var(--surface-color);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
}

.dark-mode .community-header,
.dark-mode .safety-score,
.dark-mode .stat,
.dark-mode .map-section,
.dark-mode .charts-section,
.dark-mode .report-section,
.dark-mode .recent-events {
  background-color: var(--surface-color);
}

.community-header {
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.location {
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.safety-score {
  margin-bottom: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  gap: 20px;
}

.score-large {
  font-size: 54px;
  font-weight: 700;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.stat {
  padding: 12px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
}

.details-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.map-section,
.charts-section {
  padding: 16px;
}

.community-map {
  width: 100%;
  height: 340px;
  border-radius: 8px;
}

.map-error {
  margin-top: 8px;
  color: #dc2626;
  font-size: 12px;
}

.chart {
  width: 100%;
  height: 220px;
  margin-top: 10px;
}

.report-section {
  padding: 16px;
  margin-bottom: 16px;
}

.report-content {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.report-item {
  background: var(--surface-muted);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px;
}

.dark-mode .report-item {
  background: var(--surface-muted);
  border-color: var(--border-color);
}

.report-item h4 {
  margin: 0 0 6px;
}

.report-item p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.recent-events {
  padding: 16px;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 12px 0;
}

.event-row {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  background: var(--surface-muted);
}

.dark-mode .event-row {
  background: var(--surface-muted);
  border-color: var(--border-color);
}

.event-type-badge {
  color: white;
  border-radius: 4px;
  font-size: 12px;
  padding: 3px 8px;
}

.event-info {
  font-size: 13px;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .details-grid,
  .report-content {
    grid-template-columns: 1fr;
  }
}
</style>
