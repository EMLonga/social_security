<template>
  <div class="event-detail-page" :style="{ marginTop: '70px', paddingTop: '20px' }">
    <div class="container">
      <el-button @click="$router.back()" type="info" plain>{{ t('back') }}</el-button>

      <div v-if="loading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon> {{ t('loading') }}
      </div>

      <div v-else-if="event" class="event-detail">
        <div class="detail-header">
          <h1>{{ event.title }}</h1>
          <div class="event-meta">
            <span class="event-type-tag" :style="{ backgroundColor: getEventColor(event.type) }">
              {{ getEventTypeLabel(event.type) }}
            </span>
            <span class="event-danger-tag" :class="'danger-' + event.dangerLevel">
              {{ getDangerLevelLabel(event.dangerLevel) }}
            </span>
            <span class="event-time">{{ formatDateTime(event.eventTime) }}</span>
            <span class="event-location">{{ event.address }}, {{ event.communityName || event.community }}</span>
          </div>
        </div>

        <div class="details-grid">
          <div class="main-content">
            <div id="event-map" class="event-map"></div>

            <div class="description-section">
              <h3>{{ t('description') }}</h3>
              <p>{{ event.description }}</p>
              <p v-if="event.safety_tips" class="safety-tips">
                <strong>{{ t('safetyTips') }}:</strong> {{ event.safety_tips }}
              </p>
            </div>

            <div class="action-buttons">
              <button class="btn btn-primary" @click="toggleLike" :class="{ active: event.liked }">
                {{ t('like') }} ({{ event.likes }})
              </button>
              <button class="btn btn-primary" @click="toggleSave" :class="{ active: event.saved }">
                {{ event.saved ? t('saved') : t('save') }}
              </button>
              <button class="btn btn-primary" @click="shareEvent">{{ t('share') }}</button>
              <button v-if="isLoggedIn" class="btn btn-primary" @click="exportDetails">{{ t('exportDetails') }}</button>
            </div>

            <div class="comments-section">
              <h3>{{ t('commentsTitle') }} ({{ commentsTotal }})</h3>

              <div v-if="isLoggedIn" class="comment-form">
                <textarea
                  v-model="newComment"
                  :placeholder="t('commentPlaceholder')"
                  maxlength="200"
                  rows="4"
                ></textarea>
                <div class="comment-actions">
                  <span class="char-count">{{ newComment.length }}/200</span>
                  <button @click="submitComment" class="btn btn-primary" :disabled="!newComment.trim()">
                    {{ t('postComment') }}
                  </button>
                </div>
              </div>
              <div v-else class="login-prompt">
                <p>{{ t('pleaseLoginToComment') }} <router-link to="/auth?mode=login">{{ t('login') }}</router-link> {{ t('toComment') }}</p>
              </div>

              <div class="comments-list">
                <div v-for="comment in comments" :key="comment.id" class="comment-item">
                  <div class="comment-header">
                    <strong>{{ comment.user?.username || 'Anonymous' }}</strong>
                    <span class="comment-time">{{ formatTime(comment.createdAt) }}</span>
                  </div>
                  <p class="comment-text">{{ comment.content }}</p>
                  <button v-if="isMyComment(comment.id)" class="delete-btn" @click="deleteComment(comment.id)">
                    {{ t('delete') }}
                  </button>
                </div>
                <p v-if="comments.length === 0" class="no-comments">{{ t('noCommentsYet') }}</p>
              </div>
            </div>
          </div>

          <aside class="sidebar">
            <div class="info-box">
              <h4>{{ t('eventInformation') }}</h4>
              <div class="info-item">
                <label>{{ t('date') }}</label>
                <span>{{ formatDate(event.eventTime) }}</span>
              </div>
              <div class="info-item">
                <label>{{ t('community') }}</label>
                <span @click="goToCommunity(event.communityId)" style="cursor: pointer; color: #409eff">
                  {{ event.communityName || event.community }}
                </span>
              </div>
              <div class="info-item">
                <label>{{ t('source') }}</label>
                <span>
                  <a v-if="event.source_url" :href="event.source_url" target="_blank" rel="noopener noreferrer">
                    {{ event.source_url }}
                  </a>
                  <span v-else>{{ event.dataSource }}</span>
                </span>
              </div>
              <div class="info-item">
                <label>{{ t('updated') }}</label>
                <span>{{ formatTime(event.updatedAt) }}</span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import L from 'leaflet'
import { useUserStore } from '../stores/app'
import { commentService, eventService } from '../services/api'
import { dateUtils, eventTypeColors, getDangerLevelLabel, getEventTypeLabel } from '../utils/helpers'
import { useI18n } from '../utils/i18n'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { t } = useI18n()

const event = ref(null)
const comments = ref([])
const commentsTotal = ref(0)
const loading = ref(false)
const newComment = ref('')
let map = null

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

const isLoggedIn = computed(() => userStore.isLoggedIn)
const getEventColor = (type) => eventTypeColors[type] || '#999'
const formatDateTime = (date) => dateUtils.formatDateTime(date)
const formatDate = (date) => dateUtils.formatDate(date)
const formatTime = (date) => dateUtils.daysAgo(date)

const loadEvent = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const eventRes = await eventService.getEventById(id)
    event.value = eventRes.data.event

    const commentsRes = await commentService.getComments(id, { page_size: 100 })
    comments.value = commentsRes.data.comments || []
    commentsTotal.value = commentsRes.data.total ?? comments.value.length
  } catch (error) {
    ElMessage.error(t('failedToLoadEventDetails'))
    console.error(error)
    event.value = null
    comments.value = []
    commentsTotal.value = 0
  } finally {
    loading.value = false
    await nextTick()
    if (event.value) {
      await initMap()
    }
  }
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
      // try next
    }
  }
  return false
}

const initMap = async () => {
  const container = document.getElementById('event-map')
  if (!container || !event.value) return
  if (map) {
    map.remove()
    map = null
  }
  if (container._leaflet_id) {
    container._leaflet_id = null
  }

  const lat = Number(event.value.latitude)
  const lng = Number(event.value.longitude)
  const hasCoords = Number.isFinite(lat) && Number.isFinite(lng)

  map = L.map('event-map', {
    zoomControl: true,
    attributionControl: true,
  })
  map.createPane('basePane')
  map.getPane('basePane').style.zIndex = '350'
  map.createPane('markerPane')
  map.getPane('markerPane').style.zIndex = '650'

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
  }

  if (hasCoords) {
    L.circleMarker([lat, lng], {
      pane: 'markerPane',
      radius: 7,
      fillColor: getEventColor(event.value.type),
      color: '#0f172a',
      weight: 2,
      fillOpacity: 0.95,
    })
      .bindPopup(event.value.title)
      .addTo(map)
    map.setView([lat, lng], 9)
  }

  map.whenReady(() => {
    map.invalidateSize()
  })
}

const toggleLike = async () => {
  if (!isLoggedIn.value) {
    router.push('/auth?mode=login')
    return
  }
  try {
    if (event.value.liked) {
      await eventService.unlikeEvent(event.value.id)
      event.value.likes = Math.max(0, (event.value.likes || 0) - 1)
    } else {
      await eventService.likeEvent(event.value.id)
      event.value.likes = (event.value.likes || 0) + 1
    }
    event.value.liked = !event.value.liked
  } catch {
    ElMessage.error(t('actionFailed'))
  }
}

const toggleSave = async () => {
  if (!isLoggedIn.value) {
    router.push('/auth?mode=login')
    return
  }
  try {
    if (event.value.saved) {
      await eventService.unsaveEvent(event.value.id)
      ElMessage.success(t('removedFromSaved'))
    } else {
      await eventService.saveEvent(event.value.id)
      ElMessage.success(t('savedSuccessfully'))
    }
    event.value.saved = !event.value.saved
  } catch {
    ElMessage.error(t('actionFailed'))
  }
}

const shareEvent = () => {
  navigator.clipboard.writeText(window.location.href)
  ElMessage.success(t('linkCopied'))
}

const exportDetails = () => {
  if (!event.value) return
  const content = [
    `Event Title: ${event.value.title}`,
    `Community: ${event.value.communityName || event.value.community}`,
    `Type: ${event.value.type}`,
    `Danger Level: ${event.value.dangerLevel}`,
    `Date: ${formatDateTime(event.value.eventTime)}`,
    `Location: ${event.value.address}`,
    `Source: ${event.value.source_url || event.value.dataSource}`,
    '',
    `Description: ${event.value.description || ''}`,
  ].join('\n')

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `event-${event.value.id}-details.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const submitComment = async () => {
  if (!newComment.value.trim()) return
  try {
    await commentService.createComment(event.value.id, { content: newComment.value.trim() })
    newComment.value = ''
    const commentsRes = await commentService.getComments(event.value.id, { page_size: 100 })
    comments.value = commentsRes.data.comments || []
    commentsTotal.value = commentsRes.data.total ?? comments.value.length
    event.value.commentCount = commentsTotal.value
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('failedToPostComment'))
  }
}

const deleteComment = async (commentId) => {
  try {
    await commentService.deleteComment(event.value.id, commentId)
    comments.value = comments.value.filter((item) => item.id !== commentId)
    commentsTotal.value = Math.max(0, commentsTotal.value - 1)
    event.value.commentCount = commentsTotal.value
  } catch {
    ElMessage.error(t('failedToDeleteComment'))
  }
}

const isMyComment = (commentId) => {
  const comment = comments.value.find((item) => item.id === commentId)
  return comment?.userId === userStore.user?.id
}

const goToCommunity = (communityId) => {
  router.push(`/communities/${communityId}`)
}

onMounted(loadEvent)

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<style scoped>
.event-detail-page {
  background-color: var(--bg-color);
  min-height: calc(100vh - 70px);
  padding-bottom: 40px;
}

.dark-mode .event-detail-page {
  background-color: transparent;
}

.detail-header,
.main-content,
.info-box {
  background-color: var(--surface-color);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
}

.dark-mode .detail-header,
.dark-mode .main-content,
.dark-mode .info-box {
  background-color: var(--surface-color);
}

.detail-header {
  padding: 24px;
  margin-bottom: 20px;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #6b7280;
}

.event-type-tag,
.event-danger-tag {
  color: white;
  border-radius: 4px;
  font-size: 12px;
  padding: 3px 8px;
}

.danger-low {
  background: #22c55e;
}

.danger-medium {
  background: #f59e0b;
}

.danger-high {
  background: #ef4444;
}

.details-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.main-content {
  padding: 20px;
}

.event-map {
  width: 100%;
  height: 320px;
  border-radius: 8px;
}

.description-section {
  margin-top: 16px;
}

.safety-tips {
  background: #eff6ff;
  padding: 10px;
  border-left: 4px solid #3b82f6;
  border-radius: 4px;
}

.action-buttons {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.comments-section {
  margin-top: 24px;
}

.comment-form textarea {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  resize: vertical;
}

.comment-actions {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comments-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment-item {
  background: var(--surface-muted);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px;
}

.dark-mode .comment-item {
  background: var(--surface-muted);
  border-color: var(--border-color);
}

.comment-header {
  display: flex;
  justify-content: space-between;
}

.comment-time {
  font-size: 12px;
  color: #6b7280;
}

.delete-btn {
  border: none;
  background: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 12px;
  margin-top: 6px;
}

.info-box {
  padding: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
  font-size: 13px;
}

.info-item label {
  font-weight: 600;
  color: #6b7280;
}

.no-comments {
  color: #6b7280;
  font-size: 13px;
}

@media (max-width: 900px) {
  .details-grid {
    grid-template-columns: 1fr;
  }
}
</style>
