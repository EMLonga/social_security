<template>
  <div class="home-page" :style="{ marginTop: '70px' }">
    <section class="map-section">
      <div id="home-map" class="map-container">
        <div v-if="isMapLoading" class="map-loading">
          <div class="loading-spinner"></div>
          <p>{{ t('loading') }}</p>
        </div>
      </div>
      <div class="map-controls">
        <div class="filter-panel">
          <div class="filter-group">
            <label>{{ t('eventType') }}</label>
            <el-select v-model="selectedEventType" :placeholder="t('all')" size="small" @change="loadData">
              <el-option :label="t('all')" value="" />
              <el-option :label="t('flood')" value="theft" />
              <el-option :label="t('earthquake')" value="shooting" />
              <el-option :label="t('fireRisk')" value="fire" />
              <el-option :label="t('generalAlert')" value="security" />
              <el-option :label="t('severeStorm')" value="fraud" />
            </el-select>
          </div>
          <div class="filter-group">
            <label>{{ t('timeRange') }}</label>
            <el-select v-model="selectedTimeRange" placeholder="30" size="small" @change="loadData">
              <el-option :label="`7 ${t('daysAgo')}`" value="7" />
              <el-option :label="`30 ${t('daysAgo')}`" value="30" />
              <el-option :label="`90 ${t('daysAgo')}`" value="90" />
            </el-select>
          </div>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <div class="content-grid">
          <div class="hot-events">
            <h3>{{ t('hotEvents') }}</h3>
            <div class="events-list">
              <div v-for="event in hotEvents" :key="event.id" class="event-card" @click="goDetail(event.id)">
                <div class="event-type-badge" :style="{ backgroundColor: getEventColor(event.type) }">
                  {{ getEventTypeLabel(event.type) }}
                </div>
                <h4>{{ event.title }}</h4>
                <p class="event-meta">{{ event.community }} - {{ formatTime(event.eventTime) }}</p>
                <p class="event-desc">{{ truncateText(event.description, 80) }}</p>
                <div class="event-stats">
                  <span>{{ t('like') }} {{ event.likes }}</span>
                  <span>{{ t('comments') }} {{ event.commentCount }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="safety-index">
            <h3>{{ t('safestCommunities') }}</h3>
            <div class="index-list">
              <div v-for="community in topCommunities" :key="community.id" class="index-item">
                <div class="rank">{{ community.rank }}</div>
                <div class="info">
                  <h5>{{ community.name }}</h5>
                  <p>{{ community.state }}</p>
                </div>
                <div class="score">{{ community.safetyScore }}</div>
                <div class="trend" :class="{ up: community.trend === 'up', down: community.trend === 'down' }">
                  {{ community.trend === 'up' ? t('up') : community.trend === 'down' ? t('down') : t('stable') }}
                </div>
              </div>
            </div>
            <div class="stats">
              <div class="stat">
                <div class="stat-number">{{ totalCommunities }}</div>
                <div class="stat-label">{{ t('communities') }}</div>
              </div>
              <div class="stat">
                <div class="stat-number">{{ totalEvents }}</div>
                <div class="stat-label">{{ t('eventsLabel') }}</div>
              </div>
              <div class="stat">
                <div class="stat-number">{{ todayNewEvents }}</div>
                <div class="stat-label">{{ t('newToday') }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import { communityService, eventService } from '../services/api'
import { dateUtils, eventTypeColors, getEventTypeLabel } from '../utils/helpers'
import { useI18n } from '../utils/i18n'

const router = useRouter()
const { t } = useI18n()

const selectedEventType = ref('')
const selectedTimeRange = ref('30')
const mapEvents = ref([])
const hotEvents = ref([])
const topCommunities = ref([])
const totalCommunities = ref(0)
const totalEvents = ref(0)
const todayNewEvents = ref(0)
const isMapLoading = ref(false)

let map = null
const GEOJSON_CANDIDATE_PATHS = [
  `${import.meta.env.BASE_URL}countries.geojson`,
  '/countries.geojson',
  './countries.geojson',
]

const getEventColor = (type) => eventTypeColors[type] || '#999'
const formatTime = (date) => dateUtils.daysAgo(date)

const truncateText = (text, maxLen = 80) => {
  if (!text) return ''
  return text.length > maxLen ? `${text.slice(0, maxLen)}...` : text
}

const goDetail = (id) => router.push(`/events/${id}`)
const getEventCommunityLabel = (event) =>
  event.communityName || event.community || (event.communityId ? `Community #${event.communityId}` : 'Community')

const markerAngleByType = {
  theft: 0,
  shooting: 60,
  fire: 120,
  security: 180,
  fraud: 240,
  other: 300,
}

const buildSeparatedMarkerPoints = (events = []) => {
  const cellSize = 0.22
  const grouped = new Map()
  const points = []

  events.forEach((event) => {
    const lat = Number(event.latitude)
    const lng = Number(event.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      points.push({ event, lat, lng, valid: false })
      return
    }

    const cellLat = Math.round(lat / cellSize)
    const cellLng = Math.round(lng / cellSize)
    const cellKey = `${cellLat}_${cellLng}`
    const group = grouped.get(cellKey) || []
    const point = { event, lat, lng, valid: true }
    group.push(point)
    grouped.set(cellKey, group)
    points.push(point)
  })

  grouped.forEach((group) => {
    if (group.length <= 1) return
    const centerLat = group.reduce((sum, p) => sum + p.lat, 0) / group.length
    const lngScale = Math.max(Math.cos((centerLat * Math.PI) / 180), 0.3)

    group.forEach((point, idx) => {
      const ringSize = 10
      const ring = Math.floor(idx / ringSize)
      const slot = idx % ringSize
      const baseAngle = markerAngleByType[point.event.type || 'other'] ?? 0
      const angleDeg = baseAngle + slot * (360 / ringSize) + ring * 17
      const angle = (angleDeg * Math.PI) / 180
      const radius = 0.12 + ring * 0.08
      point.lat += radius * Math.sin(angle)
      point.lng += (radius * Math.cos(angle)) / lngScale
    })
  })

  const validPoints = points.filter((p) => p.valid)
  const minDistance = 0.14
  const iterations = 5

  for (let iter = 0; iter < iterations; iter += 1) {
    for (let i = 0; i < validPoints.length; i += 1) {
      for (let j = i + 1; j < validPoints.length; j += 1) {
        const a = validPoints[i]
        const b = validPoints[j]
        const avgLat = (a.lat + b.lat) / 2
        const lngScale = Math.max(Math.cos((avgLat * Math.PI) / 180), 0.3)
        const dx = (a.lng - b.lng) * lngScale
        const dy = a.lat - b.lat
        const distance = Math.sqrt(dx * dx + dy * dy)
        if (distance >= minDistance) continue

        if (distance === 0) {
          const nudge = minDistance / 2
          a.lat += nudge
          b.lat -= nudge
          a.lng += nudge / 2
          b.lng -= nudge / 2
          continue
        }

        const overlap = (minDistance - distance) / 2
        const ux = dx / distance
        const uy = dy / distance

        a.lat += uy * overlap
        b.lat -= uy * overlap
        a.lng += (ux * overlap) / lngScale
        b.lng -= (ux * overlap) / lngScale
      }
    }
  }

  validPoints.forEach((point) => {
    point.lat = Math.max(-85, Math.min(85, point.lat))
    point.lng = Math.max(-180, Math.min(180, point.lng))
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

const initMap = async () => {
  const container = document.getElementById('home-map')
  if (!container) return
  if (map) {
    map.remove()
    map = null
  }
  if (container._leaflet_id) {
    container._leaflet_id = null
  }

  isMapLoading.value = true
  map = L.map('home-map', {
    zoomControl: true,
    attributionControl: true,
  })
  map.createPane('basePane')
  map.getPane('basePane').style.zIndex = '350'
  map.createPane('markerPane')
  map.getPane('markerPane').style.zIndex = '650'

  map.setView([45, -100], 3)
  map.setMinZoom(2)
  map.setMaxZoom(8)
  map.setMaxBounds([
    [-85, -180],
    [85, 180],
  ])
  map.getContainer().style.background = '#a9d7f5'
  const hasWorldLayer = await loadWorldGeojsonLayer(map)
  if (!hasWorldLayer) {
    L.rectangle(
      [
        [-85, -180],
        [85, 180],
      ],
      {
        pane: 'basePane',
        color: '#475569',
        weight: 1,
        fillColor: '#d4d7bd',
        fillOpacity: 0.75,
      }
    ).addTo(map)
    console.error('Failed to load geojson map on Home')
  }

  map.whenReady(() => {
    isMapLoading.value = false
    map.invalidateSize()
  })

  const separatedPoints = buildSeparatedMarkerPoints(mapEvents.value)
  separatedPoints.forEach(({ event, lat, lng, valid }) => {
    if (!valid) return
    L.circleMarker([lat, lng], {
      radius: 5,
      fillColor: getEventColor(event.type),
      pane: 'markerPane',
      color: '#0f172a',
      weight: 1,
      fillOpacity: 0.9,
    }).bindPopup(`<b>${event.title}</b><br>${getEventCommunityLabel(event)}`)
      .addTo(map)
  })
}

const loadData = async () => {
  const [eventsRes, mapRes, communitiesRes] = await Promise.allSettled([
    eventService.getEvents({
      limit: 10,
      sortBy: 'likes',
      timeRange: selectedTimeRange.value,
      eventType: selectedEventType.value || undefined,
    }),
    eventService.getEvents({
      // backend page_size upper limit is 100
      limit: 100,
      sortBy: 'publishTime',
      timeRange: selectedTimeRange.value,
      eventType: selectedEventType.value || undefined,
    }),
    communityService.getCommunities({ limit: 5, sortBy: 'safety_score', sortOrder: 'desc' }),
  ])

  if (eventsRes.status === 'fulfilled') {
    hotEvents.value = eventsRes.value.data.events || []
    totalEvents.value = eventsRes.value.data.total || 0
    todayNewEvents.value = hotEvents.value.filter((item) => {
      const ms = Date.now() - new Date(item.createdAt).getTime()
      return ms >= 0 && ms < 24 * 60 * 60 * 1000
    }).length
  } else {
    hotEvents.value = []
    totalEvents.value = 0
    todayNewEvents.value = 0
    console.error('Failed to load hot events', eventsRes.reason)
  }

  if (mapRes.status === 'fulfilled') {
    mapEvents.value = mapRes.value.data.events || []
  } else {
    mapEvents.value = []
    console.error('Failed to load map events', mapRes.reason)
  }

  if (communitiesRes.status === 'fulfilled') {
    topCommunities.value = (communitiesRes.value.data.communities || [])
      .sort((a, b) => (b.safetyScore || 0) - (a.safetyScore || 0))
      .slice(0, 5)
      .map((item, idx) => ({ ...item, rank: idx + 1 }))
    totalCommunities.value = communitiesRes.value.data.total || 0
  } else {
    topCommunities.value = []
    totalCommunities.value = 0
    console.error('Failed to load top communities', communitiesRes.reason)
  }

  await nextTick()
  await initMap()
}

onMounted(async () => {
  try {
    await loadData()
  } catch (error) {
    console.error('Failed to load home data', error)
  }
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<style scoped>
.home-page {
  background-color: var(--bg-color);
}

.dark-mode .home-page {
  background-color: transparent;
}

.map-section {
  position: relative;
  height: 60vh;
  min-height: 480px;
  margin: 20px 0;
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #c9ecff 0%, #8fd0f6 100%);
}

.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  text-align: center;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.map-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #d5e2f3;
  border-radius: 12px;
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.14);
  padding: 12px;
  z-index: 1001;
}

.dark-mode .map-controls {
  background: rgba(17, 27, 45, 0.92);
  border-color: #2d415e;
  box-shadow: 0 12px 22px rgba(2, 6, 23, 0.55);
}

.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  font-size: 12px;
  font-weight: 600;
}

.content-section {
  padding: 32px 0;
  background: transparent;
}

.dark-mode .content-section {
  background: transparent;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.event-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
}

.dark-mode .event-card {
  background: var(--surface-color);
  border-color: var(--border-color);
}

.event-type-badge {
  color: white;
  font-size: 12px;
  border-radius: 4px;
  display: inline-block;
  padding: 3px 8px;
  margin-bottom: 8px;
}

.event-meta,
.event-desc,
.event-stats {
  font-size: 12px;
  color: #6b7280;
}

.event-stats {
  display: flex;
  gap: 14px;
  margin-top: 8px;
}

.index-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.index-item {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 10px;
  display: grid;
  grid-template-columns: 36px 1fr auto auto;
  gap: 10px;
  align-items: center;
}

.dark-mode .index-item {
  background: var(--surface-color);
  border-color: var(--border-color);
}

.rank {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #409eff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.score {
  font-weight: 700;
}

.trend.up {
  color: #16a34a;
}

.trend.down {
  color: #dc2626;
}

.stats {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stat {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  text-align: center;
  padding: 10px;
  box-shadow: var(--shadow-soft);
}

.dark-mode .stat {
  background: var(--surface-color);
  border-color: var(--border-color);
}

.stat-number {
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  color: #6b7280;
  font-size: 12px;
}

@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .map-section {
    min-height: 340px;
  }
}
</style>
