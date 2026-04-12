<template>
  <div class="event-list-page" :style="{ marginTop: '70px', paddingTop: '20px' }">
    <div class="container">
      <div class="filter-section">
        <div class="filter-row">
          <el-input
            v-model="filters.search"
            :placeholder="`${t('search')}...`"
            style="width: 250px"
            clearable
            @keyup.enter="applyFilters"
          />

          <el-select v-model="filters.eventType" multiple :placeholder="t('eventType')" style="width: 150px">
            <el-option :label="t('flood')" value="theft" />
            <el-option :label="t('earthquake')" value="shooting" />
            <el-option :label="t('fireRisk')" value="fire" />
            <el-option :label="t('generalAlert')" value="security" />
            <el-option :label="t('severeStorm')" value="fraud" />
          </el-select>

          <el-select v-model="filters.community" :placeholder="t('community')" style="width: 170px" clearable>
            <el-option
              v-for="community in communities"
              :key="community.id"
              :label="community.name"
              :value="community.id"
            />
          </el-select>

          <el-select v-model="filters.timeRange" :placeholder="t('timeRange')" style="width: 150px">
            <el-option :label="`7 ${t('daysAgo')}`" value="7" />
            <el-option :label="`30 ${t('daysAgo')}`" value="30" />
            <el-option :label="`90 ${t('daysAgo')}`" value="90" />
          </el-select>

          <el-select v-model="filters.dangerLevel" :placeholder="t('dangerLevel')" style="width: 150px" clearable>
            <el-option :label="t('low')" value="low" />
            <el-option :label="t('medium')" value="medium" />
            <el-option :label="t('high')" value="high" />
          </el-select>

          <el-select v-model="filters.sortBy" :placeholder="t('sortBy')" style="width: 150px">
            <el-option :label="t('latest')" value="publishTime" />
            <el-option :label="t('mostLiked')" value="likes" />
            <el-option :label="t('mostComments')" value="comments" />
          </el-select>

          <button class="btn btn-primary" @click="applyFilters">{{ t('filter') }}</button>
          <button class="btn" @click="resetFilters">{{ t('reset') }}</button>
        </div>

        <div class="result-count">
          {{ t('results') }}: <strong>{{ totalCount }}</strong> {{ t('eventsLabel') }}
        </div>
      </div>

      <div v-if="loading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon> {{ t('loading') }}
      </div>

      <div v-else-if="events.length === 0" class="empty-state">
        <p>{{ t('noEvents') }}</p>
      </div>

      <div v-else class="events-grid">
        <div v-for="event in events" :key="event.id" class="event-card" @click="goDetail(event.id)">
          <div class="event-header">
            <span class="event-type-tag" :style="{ backgroundColor: getEventColor(event.type) }">
              {{ getEventTypeLabel(event.type) }}
            </span>
            <span class="event-danger-tag" :class="'danger-' + event.dangerLevel">
              {{ getDangerLevelLabel(event.dangerLevel) }}
            </span>
          </div>

          <h3 class="event-title">{{ event.title }}</h3>

          <div class="event-info">
            <p><strong>{{ t('time') }}:</strong> {{ formatDateTime(event.eventTime) }}</p>
            <p><strong>{{ t('location') }}:</strong> {{ event.address }}, {{ event.community }}</p>
            <p><strong>{{ t('source') }}:</strong> {{ event.dataSource }}</p>
          </div>

          <p class="event-desc">{{ event.description.substring(0, 100) }}...</p>

          <div class="event-footer">
            <div class="event-stats">
              <span>{{ t('like') }} {{ event.likes }}</span>
              <span>{{ t('comments') }} {{ event.commentCount }}</span>
            </div>
            <div class="event-actions">
              <button class="icon-btn" @click.stop="toggleLike(event.id)" :class="{ active: event.liked }">
                ♥
              </button>
              <button class="icon-btn" @click.stop="toggleSave(event.id)" :class="{ active: event.saved }">
                ★
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button
          v-for="page in totalPages"
          :key="page"
          :class="{ active: currentPage === page }"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { eventService, communityService } from '../services/api'
import { getEventTypeLabel, getDangerLevelLabel, dateUtils, eventTypeColors } from '../utils/helpers'
import { useI18n } from '../utils/i18n'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()

const events = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)
const communities = ref([])

const { t } = useI18n()

const filters = ref({
  search: '',
  eventType: [],
  community: null,
  timeRange: '30',
  dangerLevel: null,
  sortBy: 'publishTime',
})

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

const getEventColor = (type) => eventTypeColors[type] || '#999'
const formatDateTime = (date) => dateUtils.formatDateTime(date)

const loadEvents = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      search: filters.value.search || undefined,
      event_types: filters.value.eventType.length ? filters.value.eventType : undefined,
      community: filters.value.community ? Number(filters.value.community) : undefined,
      timeRange: filters.value.timeRange,
      dangerLevel: filters.value.dangerLevel,
      sortBy: filters.value.sortBy,
    }
    const res = await eventService.getEvents(params)
    events.value = res.data.events || []
    totalCount.value = res.data.total || 0
  } catch (error) {
    ElMessage.error(t('failedToLoadEvents'))
    console.error(error)
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  currentPage.value = 1
  loadEvents()
}

const resetFilters = () => {
  filters.value = {
    search: '',
    eventType: [],
    community: null,
    timeRange: '30',
    dangerLevel: null,
    sortBy: 'publishTime',
  }
  currentPage.value = 1
  loadEvents()
}

const loadCommunities = async () => {
  try {
    const res = await communityService.getCommunities({ limit: 100, sortBy: 'safety_score', sortOrder: 'desc' })
    communities.value = res.data.communities || []
  } catch (error) {
    console.error('Failed to load communities', error)
  }
}

const goDetail = (id) => {
  router.push(`/events/${id}`)
}

const goToPage = (page) => {
  currentPage.value = page
  loadEvents()
}

const toggleLike = async (id) => {
  try {
    const event = events.value.find((e) => e.id === id)
    if (event.liked) {
      await eventService.unlikeEvent(id)
      event.likes = Math.max(0, (event.likes || 0) - 1)
    } else {
      await eventService.likeEvent(id)
      event.likes = (event.likes || 0) + 1
    }
    event.liked = !event.liked
  } catch (error) {
    ElMessage.error(t('actionFailed'))
  }
}

const toggleSave = async (id) => {
  try {
    const event = events.value.find((e) => e.id === id)
    if (event.saved) {
      await eventService.unsaveEvent(id)
    } else {
      await eventService.saveEvent(id)
    }
    event.saved = !event.saved
  } catch (error) {
    ElMessage.error(t('actionFailed'))
  }
}

onMounted(() => {
  filters.value.search = route.query.search || ''
  if (route.query.community) {
    filters.value.community = Number(route.query.community) || null
  }
  loadCommunities()
  loadEvents()
})

watch(
  () => route.query.search,
  (newSearch) => {
    filters.value.search = newSearch || ''
    currentPage.value = 1
    loadEvents()
  }
)

watch(
  () => route.query.community,
  (newCommunity) => {
    filters.value.community = newCommunity ? Number(newCommunity) : null
    currentPage.value = 1
    loadEvents()
  }
)
</script>

<style scoped>
.event-list-page {
  background-color: var(--bg-color);
  min-height: calc(100vh - 70px);
}

.dark-mode .event-list-page {
  background-color: transparent;
}

.filter-section {
  background-color: var(--surface-color);
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: var(--shadow-soft);
  margin-bottom: 20px;
}

.dark-mode .filter-section {
  background-color: var(--surface-color);
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 15px;
}

.result-count {
  color: #666;
  font-size: 14px;
}

.dark-mode .result-count {
  color: #aaa;
}

.events-grid {
  display: grid;
  gap: 16px;
}

.event-card {
  background-color: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: var(--shadow-soft);
}

.dark-mode .event-card {
  background-color: var(--surface-color);
  border-color: var(--border-color);
}

.event-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.event-header {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.event-type-tag,
.event-danger-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  font-weight: 500;
}

.danger-low {
  background-color: #67c23a;
}

.danger-medium {
  background-color: #e6a23c;
}

.danger-high {
  background-color: #f56c6c;
}

.event-title {
  margin: 10px 0;
  font-size: 16px;
}

.event-info {
  font-size: 13px;
  color: #666;
  margin: 10px 0;
}

.dark-mode .event-info {
  color: #aaa;
}

.event-info p {
  margin: 4px 0;
}

.event-desc {
  color: #666;
  font-size: 13px;
  line-height: 1.5;
  margin: 10px 0;
}

.dark-mode .event-desc {
  color: #aaa;
}

.event-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

.dark-mode .event-footer {
  border-top-color: #333;
}

.event-stats {
  display: flex;
  gap: 15px;
  font-size: 13px;
  color: #666;
}

.event-actions {
  display: flex;
  gap: 10px;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  transition: transform 0.2s;
}

.icon-btn:hover {
  transform: scale(1.2);
}

.icon-btn.active {
  filter: saturate(1.5);
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 30px;
  margin-bottom: 20px;
}

.pagination button {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  background-color: var(--surface-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.dark-mode .pagination button {
  background-color: var(--surface-color);
  border-color: var(--border-color);
}

.pagination button.active {
  background-color: #409eff;
  color: white;
  border-color: #409eff;
}

.pagination button:hover:not(.active) {
  border-color: #409eff;
}

@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
  }

  .filter-row > * {
    width: 100%;
  }
}
</style>
