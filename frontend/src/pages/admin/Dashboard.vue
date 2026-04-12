<template>
  <div class="admin-page" :style="{ marginTop: '70px' }">
    <div class="admin-layout">
      <aside class="admin-sidebar">
        <nav class="admin-nav">
          <button
            v-for="item in adminMenuItems"
            :key="item.id"
            :class="{ active: activeTab === item.id }"
            class="admin-nav-item"
            @click="switchTab(item.id)"
          >
            {{ item.label }}
          </button>
        </nav>
        <button class="btn btn-danger sidebar-logout" @click="logout">{{ t('logout') }}</button>
      </aside>

      <main class="admin-content">
        <section v-if="activeTab === 'overview'" class="admin-section">
          <h2>{{ t('adminDataOverview') }}</h2>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">{{ t('adminTotalUsers') }}</div>
              <div class="stat-value">{{ stats.totalUsers }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">{{ t('adminTotalCommunities') }}</div>
              <div class="stat-value">{{ stats.totalCommunities }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">{{ t('adminTotalEvents') }}</div>
              <div class="stat-value">{{ stats.totalEvents }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">{{ t('adminTotalComments') }}</div>
              <div class="stat-value">{{ stats.totalComments }}</div>
            </div>
          </div>
          <div class="sub-grid">
            <div class="panel">
              <h3>{{ t('adminToday') }}</h3>
              <p>{{ t('adminNewEvents') }}: {{ stats.todayNewEvents }}</p>
              <p>{{ t('adminNewUsers') }}: {{ stats.todayNewUsers }}</p>
            </div>
            <div class="panel">
              <h3>{{ t('adminSpiderStatus') }}</h3>
              <p>{{ t('adminRunning') }}: {{ spiderStatus.is_running ? t('yes') : t('no') }}</p>
              <p>{{ t('adminSuccess') }}: {{ spiderStatus.success_count || 0 }}</p>
              <p>{{ t('adminFailed') }}: {{ spiderStatus.failure_count || 0 }}</p>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'events'" class="admin-section">
          <div class="section-head">
            <h2>{{ t('adminEventManagement') }}</h2>
            <div class="filters">
              <el-select v-model="eventFilterType" :placeholder="t('eventType')" clearable @change="onEventFilterChange">
                <el-option :label="t('flood')" value="theft" />
                <el-option :label="t('earthquake')" value="shooting" />
                <el-option :label="t('fireRisk')" value="fire" />
                <el-option :label="t('generalAlert')" value="security" />
                <el-option :label="t('severeStorm')" value="fraud" />
              </el-select>
              <el-button @click="loadAdminEvents">{{ t('adminRefresh') }}</el-button>
            </div>
          </div>
          <el-table :data="adminEvents" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="title" :label="t('adminTitle')" min-width="180" />
            <el-table-column :label="t('adminType')" width="150">
              <template #default="{ row }">
                {{ getEventTypeDisplay(row.event_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="danger_level" :label="t('adminDanger')" width="120" />
            <el-table-column prop="community.name" :label="t('community')" width="170" />
            <el-table-column :label="t('adminActions')" width="180">
              <template #default="{ row }">
                <el-button size="small" @click="openEventEdit(row)">{{ t('adminEdit') }}</el-button>
                <el-button size="small" type="danger" @click="removeEvent(row.id)">{{ t('delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              v-model:current-page="eventPagination.page"
              v-model:page-size="eventPagination.pageSize"
              :total="eventPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="loadAdminEvents"
              @size-change="onEventPageSizeChange"
            />
          </div>
        </section>

        <section v-if="activeTab === 'communities'" class="admin-section">
          <div class="section-head">
            <h2>{{ t('adminCommunityManagement') }}</h2>
            <div class="filters">
              <el-button type="primary" @click="openCommunityCreate">{{ t('adminAddCommunity') }}</el-button>
              <el-button @click="loadAdminCommunities">{{ t('adminRefresh') }}</el-button>
            </div>
          </div>
          <el-table :data="adminCommunities" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="name" :label="t('adminName')" min-width="160" />
            <el-table-column prop="state" :label="t('adminState')" width="100" />
            <el-table-column prop="city" :label="t('adminCity')" width="120" />
            <el-table-column prop="zipcode" :label="t('adminZipcode')" width="120" />
            <el-table-column prop="safety_score" :label="t('adminSafety')" width="110" />
            <el-table-column :label="t('adminActions')" width="200">
              <template #default="{ row }">
                <el-button size="small" @click="openCommunityEdit(row)">{{ t('adminEdit') }}</el-button>
                <el-button size="small" type="danger" @click="removeCommunity(row.id)">{{ t('delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              v-model:current-page="communityPagination.page"
              v-model:page-size="communityPagination.pageSize"
              :total="communityPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="loadAdminCommunities"
              @size-change="onCommunityPageSizeChange"
            />
          </div>
        </section>

        <section v-if="activeTab === 'comments'" class="admin-section">
          <div class="section-head">
            <h2>{{ t('adminCommentManagement') }}</h2>
            <div class="filters">
              <el-select v-model="commentStatus" :placeholder="t('adminStatus')" clearable @change="onCommentFilterChange">
                <el-option :label="t('adminFlagged')" value="flagged" />
              </el-select>
              <el-button @click="loadAdminComments">{{ t('adminRefresh') }}</el-button>
            </div>
          </div>
          <el-table :data="adminComments" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="user.username" :label="t('user')" width="140" />
            <el-table-column prop="event.title" :label="t('adminEvent')" min-width="180" />
            <el-table-column prop="content" :label="t('adminContent')" min-width="220" />
            <el-table-column prop="is_flagged" :label="t('adminFlagged')" width="90" />
            <el-table-column :label="t('adminActions')" width="210">
              <template #default="{ row }">
                <el-button
                  size="small"
                  @click="row.is_flagged ? unflagComment(row.id) : flagComment(row.id)"
                >
                  {{ row.is_flagged ? t('adminUnflag') : t('adminFlag') }}
                </el-button>
                <el-button size="small" type="danger" @click="removeComment(row.id)">{{ t('delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              v-model:current-page="commentPagination.page"
              v-model:page-size="commentPagination.pageSize"
              :total="commentPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="loadAdminComments"
              @size-change="onCommentPageSizeChange"
            />
          </div>
        </section>

        <section v-if="activeTab === 'users'" class="admin-section">
          <div class="section-head">
            <h2>{{ t('adminUserManagement') }}</h2>
            <div class="filters">
              <el-button @click="loadAdminUsers">{{ t('adminRefresh') }}</el-button>
            </div>
          </div>
          <el-table :data="adminUsers" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" :label="t('username')" width="140" />
            <el-table-column prop="email" :label="t('email')" min-width="200" />
            <el-table-column prop="role" :label="t('adminRole')" width="120">
              <template #default="{ row }">
                <el-select :model-value="row.role" @change="(val) => changeUserRole(row.id, val)" size="small">
                  <el-option label="user" value="user" />
                  <el-option label="admin" value="admin" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" :label="t('adminActive')" width="120">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" @change="(val) => toggleUserStatus(row.id, val)" />
              </template>
            </el-table-column>
            <el-table-column :label="t('adminActions')" width="130">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="removeUser(row.id)">{{ t('delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="table-pagination">
            <el-pagination
              v-model:current-page="userPagination.page"
              v-model:page-size="userPagination.pageSize"
              :total="userPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="loadAdminUsers"
              @size-change="onUserPageSizeChange"
            />
          </div>
        </section>

        <section v-if="activeTab === 'spider'" class="admin-section">
          <h2>{{ t('adminSpiderTasks') }}</h2>
          <div class="sub-grid">
            <div class="panel">
              <p>{{ t('adminRunning') }}: {{ spiderStatus.is_running ? t('yes') : t('no') }}</p>
              <p>{{ t('adminLastRun') }}: {{ spiderStatus.last_run || 'N/A' }}</p>
              <p>{{ t('adminSuccessCount') }}: {{ spiderStatus.success_count || 0 }}</p>
              <p>{{ t('adminFailureCount') }}: {{ spiderStatus.failure_count || 0 }}</p>
              <p v-if="spiderStatus.last_error">{{ t('adminLastError') }}: {{ spiderStatus.last_error }}</p>
            </div>
            <div class="panel panel-actions">
              <el-button type="primary" @click="triggerSpider">{{ t('adminTriggerSpider') }}</el-button>
              <el-button type="danger" @click="stopSpider">{{ t('adminStopSpider') }}</el-button>
              <el-button @click="loadSpiderStatus">{{ t('adminRefresh') }}</el-button>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'config'" class="admin-section">
          <h2>{{ t('adminSiteConfig') }}</h2>
          <el-form :model="siteConfig" label-width="160px" class="config-form">
            <el-form-item :label="t('adminSiteName')">
              <el-input v-model="siteConfig.site_name" />
            </el-form-item>
            <el-form-item :label="t('adminLogoUrl')">
              <el-input v-model="siteConfig.logo" />
            </el-form-item>
            <el-form-item :label="t('adminBilingualEnabled')">
              <el-switch v-model="siteConfig.bilingual_enabled" />
            </el-form-item>
            <el-form-item :label="t('disclaimer')">
              <el-input v-model="siteConfig.disclaimer" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item :label="t('adminDataSources')">
              <el-input v-model="siteConfig.data_sources" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
          <div class="config-actions">
            <el-button type="primary" @click="saveConfig">{{ t('adminSaveConfig') }}</el-button>
          </div>

          <div class="sensitive-section">
            <h3>{{ t('adminSensitiveWords') }}</h3>
            <div class="sensitive-actions">
              <el-input v-model="newSensitiveWord" :placeholder="t('adminAddSensitiveWord')" />
              <el-button type="primary" @click="addSensitiveWord">{{ t('adminAdd') }}</el-button>
            </div>
            <div class="word-list">
              <el-tag
                v-for="word in sensitiveWords"
                :key="word.id"
                closable
                @close="deleteSensitiveWord(word.id)"
              >
                {{ word.word }}
              </el-tag>
            </div>
          </div>
        </section>
      </main>
    </div>

    <el-dialog v-model="eventDialogVisible" :title="t('adminEditEvent')" width="500px">
      <el-form :model="eventEditForm" label-width="120px">
        <el-form-item :label="t('adminTitle')"><el-input v-model="eventEditForm.title" /></el-form-item>
        <el-form-item :label="t('description')"><el-input v-model="eventEditForm.description" type="textarea" /></el-form-item>
        <el-form-item :label="t('adminType')">
          <el-select v-model="eventEditForm.event_type">
            <el-option :label="t('flood')" value="theft" />
            <el-option :label="t('earthquake')" value="shooting" />
            <el-option :label="t('fireRisk')" value="fire" />
            <el-option :label="t('generalAlert')" value="security" />
            <el-option :label="t('severeStorm')" value="fraud" />
            <el-option :label="t('otherHazard')" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('adminDanger')">
          <el-select v-model="eventEditForm.danger_level">
            <el-option :label="t('low')" value="low" />
            <el-option :label="t('medium')" value="medium" />
            <el-option :label="t('high')" value="high" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="eventDialogVisible = false">{{ t('adminCancel') }}</el-button>
        <el-button type="primary" @click="saveEventEdit">{{ t('adminSave') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="communityDialogVisible" :title="communityEditForm.id ? t('adminEditCommunity') : t('adminCreateCommunity')" width="540px">
      <el-form :model="communityEditForm" label-width="120px">
        <el-form-item :label="t('adminName')"><el-input v-model="communityEditForm.name" /></el-form-item>
        <el-form-item :label="t('adminState')"><el-input v-model="communityEditForm.state" /></el-form-item>
        <el-form-item :label="t('adminCity')"><el-input v-model="communityEditForm.city" /></el-form-item>
        <el-form-item :label="t('adminZipcode')"><el-input v-model="communityEditForm.zipcode" /></el-form-item>
        <el-form-item :label="t('adminLatitude')"><el-input-number v-model="communityEditForm.latitude" :step="0.0001" /></el-form-item>
        <el-form-item :label="t('adminLongitude')"><el-input-number v-model="communityEditForm.longitude" :step="0.0001" /></el-form-item>
        <el-form-item :label="t('area')"><el-input-number v-model="communityEditForm.area" :step="0.1" /></el-form-item>
        <el-form-item :label="t('population')"><el-input-number v-model="communityEditForm.population" :step="100" /></el-form-item>
        <el-form-item :label="t('safetyScore')">
          <el-input-number v-model="communityEditForm.safety_score" :min="0" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="communityDialogVisible = false">{{ t('adminCancel') }}</el-button>
        <el-button type="primary" @click="saveCommunityEdit">{{ t('adminSave') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../../stores/app'
import { adminService } from '../../services/api'
import { useI18n } from '../../utils/i18n'

const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()

const activeTab = ref('overview')
const eventFilterType = ref('')
const commentStatus = ref('')

const stats = ref({
  totalUsers: 0,
  totalCommunities: 0,
  totalEvents: 0,
  totalComments: 0,
  todayNewEvents: 0,
  todayNewUsers: 0,
})

const spiderStatus = ref({})
const adminEvents = ref([])
const adminCommunities = ref([])
const adminComments = ref([])
const adminUsers = ref([])
const eventPagination = ref({ page: 1, pageSize: 20, total: 0 })
const communityPagination = ref({ page: 1, pageSize: 20, total: 0 })
const commentPagination = ref({ page: 1, pageSize: 20, total: 0 })
const userPagination = ref({ page: 1, pageSize: 20, total: 0 })

const siteConfig = ref({
  site_name: '',
  logo: '',
  bilingual_enabled: true,
  disclaimer: '',
  data_sources: '',
})
const sensitiveWords = ref([])
const newSensitiveWord = ref('')

const eventDialogVisible = ref(false)
const eventEditForm = ref({})
const communityDialogVisible = ref(false)
const communityEditForm = ref({})

const adminMenuItems = computed(() => [
  { id: 'overview', label: t('adminDataOverview') },
  { id: 'events', label: t('adminEventManagement') },
  { id: 'communities', label: t('adminCommunityManagement') },
  { id: 'comments', label: t('adminCommentManagement') },
  { id: 'users', label: t('adminUserManagement') },
  { id: 'spider', label: t('adminSpiderTasks') },
  { id: 'config', label: t('adminSiteConfig') },
])

const getEventTypeDisplay = (value) => {
  const key = String(value || '').toLowerCase()
  const labels = {
    theft: t('flood'),
    shooting: t('earthquake'),
    fire: t('fireRisk'),
    security: t('generalAlert'),
    fraud: t('severeStorm'),
    other: t('otherHazard'),
  }
  return labels[key] || key || t('adminUnknown')
}

const mapStats = (raw = {}) => ({
  totalUsers: raw.total_users || 0,
  totalCommunities: raw.total_communities || 0,
  totalEvents: raw.total_events || 0,
  totalComments: raw.total_comments || 0,
  todayNewEvents: raw.today_new_events || 0,
  todayNewUsers: raw.today_new_users || 0,
})

const loadStats = async () => {
  const res = await adminService.getDashboard()
  stats.value = mapStats(res.data.stats || {})
}

const loadSpiderStatus = async () => {
  const res = await adminService.getSpider()
  spiderStatus.value = res.data.spider_status || {}
}

const loadAdminEvents = async () => {
  const res = await adminService.getEvents({
    event_type: eventFilterType.value || undefined,
    page: eventPagination.value.page,
    page_size: eventPagination.value.pageSize,
  })
  adminEvents.value = res.data.events || []
  eventPagination.value.total = res.data.total || 0
}

const loadAdminCommunities = async () => {
  const res = await adminService.getCommunities({
    page: communityPagination.value.page,
    page_size: communityPagination.value.pageSize,
  })
  adminCommunities.value = res.data.communities || []
  communityPagination.value.total = res.data.total || 0
}

const loadAdminComments = async () => {
  const res = await adminService.getComments({
    status: commentStatus.value || undefined,
    page: commentPagination.value.page,
    page_size: commentPagination.value.pageSize,
  })
  adminComments.value = (res.data.comments || []).map((item) => ({
    ...item,
    is_flagged: item.is_flagged === true || item.is_flagged === 1 || item.is_flagged === 'true',
  }))
  commentPagination.value.total = res.data.total || 0
}

const loadAdminUsers = async () => {
  const res = await adminService.getUsers({
    page: userPagination.value.page,
    page_size: userPagination.value.pageSize,
  })
  adminUsers.value = res.data.users || []
  userPagination.value.total = res.data.total || 0
}

const onEventPageSizeChange = () => {
  eventPagination.value.page = 1
  loadAdminEvents()
}

const onEventFilterChange = () => {
  eventPagination.value.page = 1
  loadAdminEvents()
}

const onCommunityPageSizeChange = () => {
  communityPagination.value.page = 1
  loadAdminCommunities()
}

const onCommentPageSizeChange = () => {
  commentPagination.value.page = 1
  loadAdminComments()
}

const onCommentFilterChange = () => {
  commentPagination.value.page = 1
  loadAdminComments()
}

const onUserPageSizeChange = () => {
  userPagination.value.page = 1
  loadAdminUsers()
}

const loadConfig = async () => {
  const res = await adminService.getConfig()
  siteConfig.value = res.data.config || siteConfig.value
  sensitiveWords.value = res.data.sensitive_words || []
}

const openEventEdit = (row) => {
  eventEditForm.value = {
    id: row.id,
    title: row.title,
    description: row.description,
    event_type: row.event_type,
    danger_level: row.danger_level,
    address: row.address,
  }
  eventDialogVisible.value = true
}

const saveEventEdit = async () => {
  await adminService.updateEvent(eventEditForm.value.id, {
    title: eventEditForm.value.title,
    description: eventEditForm.value.description,
    event_type: eventEditForm.value.event_type,
    danger_level: eventEditForm.value.danger_level,
    address: eventEditForm.value.address,
  })
  eventDialogVisible.value = false
  ElMessage.success(t('adminEventUpdated'))
  await loadAdminEvents()
}

const removeEvent = async (id) => {
  await ElMessageBox.confirm(t('adminDeleteEventConfirm'), t('confirm'), { type: 'warning' })
  await adminService.deleteEvent(id)
  ElMessage.success(t('adminEventDeleted'))
  if (adminEvents.value.length <= 1 && eventPagination.value.page > 1) {
    eventPagination.value.page -= 1
  }
  await loadAdminEvents()
}

const openCommunityCreate = () => {
  communityEditForm.value = {
    name: '',
    state: '',
    city: '',
    zipcode: '',
    latitude: 39.8283,
    longitude: -98.5795,
    area: null,
    population: null,
    safety_score: 50,
  }
  communityDialogVisible.value = true
}

const openCommunityEdit = (row) => {
  communityEditForm.value = { ...row }
  communityDialogVisible.value = true
}

const saveCommunityEdit = async () => {
  const payload = {
    name: communityEditForm.value.name,
    state: communityEditForm.value.state,
    city: communityEditForm.value.city,
    zipcode: communityEditForm.value.zipcode,
    latitude: Number(communityEditForm.value.latitude),
    longitude: Number(communityEditForm.value.longitude),
    area: communityEditForm.value.area,
    population: communityEditForm.value.population,
    safety_score: communityEditForm.value.safety_score,
  }
  if (communityEditForm.value.id) {
    await adminService.updateCommunity(communityEditForm.value.id, payload)
  } else {
    await adminService.createCommunity(payload)
  }
  communityDialogVisible.value = false
  ElMessage.success(t('adminCommunitySaved'))
  await loadAdminCommunities()
}

const removeCommunity = async (id) => {
  await ElMessageBox.confirm(t('adminDeleteCommunityConfirm'), t('confirm'), { type: 'warning' })
  await adminService.deleteCommunity(id)
  ElMessage.success(t('adminCommunityDeleted'))
  if (adminCommunities.value.length <= 1 && communityPagination.value.page > 1) {
    communityPagination.value.page -= 1
  }
  await loadAdminCommunities()
}

const flagComment = async (id) => {
  try {
    await adminService.setCommentFlagStatus(id, true)
    const target = adminComments.value.find((item) => item.id === id)
    if (target) target.is_flagged = true
    ElMessage.success(t('adminCommentFlagged'))
    await loadAdminComments()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('actionFailed'))
  }
}

const unflagComment = async (id) => {
  try {
    await adminService.setCommentFlagStatus(id, false)

    if (commentStatus.value === 'flagged') {
      adminComments.value = adminComments.value.filter((item) => item.id !== id)
      commentPagination.value.total = Math.max(0, commentPagination.value.total - 1)
      if (adminComments.value.length === 0 && commentPagination.value.page > 1) {
        commentPagination.value.page -= 1
      }
    } else {
      const target = adminComments.value.find((item) => item.id === id)
      if (target) target.is_flagged = false
    }

    ElMessage.success(t('adminCommentUnflagged'))
    await loadAdminComments()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('actionFailed'))
  }
}

const removeComment = async (id) => {
  await ElMessageBox.confirm(t('adminDeleteCommentConfirm'), t('confirm'), { type: 'warning' })
  await adminService.deleteComment(id)
  ElMessage.success(t('commentDeleted'))
  if (adminComments.value.length <= 1 && commentPagination.value.page > 1) {
    commentPagination.value.page -= 1
  }
  await loadAdminComments()
}

const changeUserRole = async (id, role) => {
  await adminService.updateUserRole(id, role)
  ElMessage.success(t('adminRoleUpdated'))
  await loadAdminUsers()
}

const toggleUserStatus = async (id, isActive) => {
  await adminService.updateUserStatus(id, isActive)
  ElMessage.success(t('adminStatusUpdated'))
  await loadAdminUsers()
}

const removeUser = async (id) => {
  await ElMessageBox.confirm(t('adminDeleteUserConfirm'), t('confirm'), { type: 'warning' })
  await adminService.deleteUser(id)
  ElMessage.success(t('adminUserDeleted'))
  if (adminUsers.value.length <= 1 && userPagination.value.page > 1) {
    userPagination.value.page -= 1
  }
  await loadAdminUsers()
}

const triggerSpider = async () => {
  await adminService.triggerSpider()
  ElMessage.success(t('adminSpiderTriggered'))
  await loadSpiderStatus()
}

const stopSpider = async () => {
  await adminService.stopSpider()
  ElMessage.success(t('adminSpiderStopped'))
  await loadSpiderStatus()
}

const saveConfig = async () => {
  await adminService.updateConfig(siteConfig.value)
  ElMessage.success(t('adminConfigSaved'))
}

const addSensitiveWord = async () => {
  const word = newSensitiveWord.value.trim()
  if (!word) return
  await adminService.addSensitiveWord(word)
  newSensitiveWord.value = ''
  ElMessage.success(t('adminSensitiveWordAdded'))
  await loadConfig()
}

const deleteSensitiveWord = async (id) => {
  await adminService.deleteSensitiveWord(id)
  ElMessage.success(t('adminSensitiveWordDeleted'))
  await loadConfig()
}

const switchTab = async (tab) => {
  activeTab.value = tab
  try {
    if (tab === 'overview') {
      await Promise.all([loadStats(), loadSpiderStatus()])
    } else if (tab === 'events') {
      eventPagination.value.page = 1
      await loadAdminEvents()
    } else if (tab === 'communities') {
      communityPagination.value.page = 1
      await loadAdminCommunities()
    } else if (tab === 'comments') {
      commentPagination.value.page = 1
      await loadAdminComments()
    } else if (tab === 'users') {
      userPagination.value.page = 1
      await loadAdminUsers()
    } else if (tab === 'spider') {
      await loadSpiderStatus()
    } else if (tab === 'config') {
      await loadConfig()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('adminLoadFailed'))
  }
}

const logout = () => {
  userStore.logout()
  router.push('/')
}

onMounted(async () => {
  if (!userStore.isLoggedIn || userStore.user?.role !== 'admin') {
    router.push('/')
    return
  }
  await switchTab('overview')
})
</script>

<style scoped>
.admin-page {
  background-color: var(--bg-color);
}

.dark-mode .admin-page {
  background-color: transparent;
}

.admin-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  min-height: calc(100vh - 70px);
}

.admin-sidebar {
  background-color: var(--surface-color);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
  padding: 16px;
  border-radius: 12px;
  height: fit-content;
}

.dark-mode .admin-sidebar {
  background-color: var(--surface-color);
}

.admin-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.admin-nav-item {
  padding: 10px 12px;
  border: none;
  background: transparent;
  text-align: left;
  border-radius: 6px;
  cursor: pointer;
}

.admin-nav-item.active {
  background-color: #409eff;
  color: white;
}

.sidebar-logout {
  width: 100%;
  margin-top: 12px;
}

.admin-content {
  background-color: var(--surface-color);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
  padding: 20px;
  border-radius: 12px;
}

.dark-mode .admin-content {
  background-color: var(--surface-color);
}

.admin-section h2 {
  margin: 0 0 14px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.filters {
  display: flex;
  gap: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
  padding: 14px;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
}

.sub-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.panel {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface-muted);
}

.dark-mode .panel {
  border-color: var(--border-color);
}

.panel-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-form {
  max-width: 760px;
}

.config-actions {
  margin-top: 8px;
}

.sensitive-section {
  margin-top: 18px;
}

.sensitive-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.word-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.table-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 980px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .sub-grid {
    grid-template-columns: 1fr;
  }
}
</style>
