<template>
  <div class="user-center-page" :style="{ marginTop: '70px' }">
    <div class="container" style="display: grid; grid-template-columns: 200px 1fr; gap: 20px; min-height: calc(100vh - 70px)">
      <aside class="sidebar">
        <nav class="sidebar-nav">
          <button
            v-for="item in navItems"
            :key="item.id"
            :class="{ active: activeTab === item.id }"
            @click="activeTab = item.id"
            class="nav-item"
          >
            {{ item.label }}
          </button>
        </nav>
      </aside>

      <main class="main-content">
        <div v-if="activeTab === 'profile'" class="tab-content">
          <h2>{{ t('myProfile') }}</h2>
          <div class="profile-form">
            <div class="form-group">
              <label>{{ t('username') }}</label>
              <input v-model="profileForm.username" type="text" />
            </div>
            <div class="form-group">
              <label>{{ t('email') }}</label>
              <input v-model="profileForm.email" type="email" />
            </div>
            <div class="form-group">
              <label>{{ t('currentPassword') }}</label>
              <input v-model="profileForm.currentPassword" type="password" :placeholder="t('requiredToChange')" />
            </div>
            <div class="form-group">
              <label>{{ t('newPasswordOptional') }}</label>
              <input v-model="profileForm.newPassword" type="password" :placeholder="t('leaveBlankKeepCurrent')" />
            </div>
            <div class="form-actions">
              <button class="btn btn-primary" @click="updateProfile">{{ t('saveChanges') }}</button>
              <button class="btn" @click="logout">{{ t('logoutBtn') }}</button>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'saved'" class="tab-content">
          <h2>{{ t('mySavedEvents') }}</h2>
          <div v-if="savedEvents.length === 0" class="empty-state">
            <p>{{ t('noSavedEvents') }}</p>
          </div>
          <div v-else class="events-list">
            <div v-for="event in savedEvents" :key="event.id" class="event-item">
              <div class="event-header">
                <h4 @click="goToEvent(event.id)" class="event-title">{{ event.title }}</h4>
                <button class="remove-btn" @click="removeSavedEvent(event.id)">{{ t('remove') }}</button>
              </div>
              <p class="event-meta">{{ localizeCommunityName(event.community || event.community_id || event.communityId || t('community'), event.communityState, event.communityCity) }} - {{ formatTime(event.eventTime) }}</p>
              <p class="event-desc">{{ truncateText(event.description, 80) }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'followed'" class="tab-content">
          <h2>{{ t('myFollowedCommunities') }}</h2>
          <div v-if="followedCommunities.length === 0" class="empty-state">
            <p>{{ t('noFollowedCommunities') }}</p>
          </div>
          <div v-else class="communities-list">
            <div v-for="community in followedCommunities" :key="community.id" class="community-item">
              <div class="community-header">
                <h4 @click="goToCommunity(community.id)" class="community-name">{{ localizeCommunityName(community.name, community.state, community.city) }}</h4>
                <button class="remove-btn" @click="unfollowCommunity(community.id)">{{ t('unfollow') }}</button>
              </div>
              <p class="community-meta">{{ localizeCommunityName(community.name, community.state, community.city) }} - {{ t('safetyScore') }}: {{ community.safetyScore }}</p>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'comments'" class="tab-content">
          <h2>{{ t('myComments') }}</h2>
          <div v-if="myComments.length === 0" class="empty-state">
            <p>{{ t('noMyComments') }}</p>
          </div>
          <div v-else class="comments-list">
            <div v-for="comment in myComments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-date">{{ formatTime(comment.createdAt) }}</span>
                <button class="delete-btn" @click="deleteMyComment(comment.id)">{{ t('delete') }}</button>
              </div>
              <p class="comment-event">{{ t('onEvent') }}: <a @click="goToEvent(comment.eventId || comment.event_id)">{{ comment.event?.title || comment.eventTitle || comment.event_id || t('events') }}</a></p>
              <p class="comment-text">{{ comment.content }}</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/app'
import { userService, eventService, communityService, commentService } from '../services/api'
import { dateUtils, localizeCommunityName } from '../utils/helpers'
import { ElMessage } from 'element-plus'
import { useI18n } from '../utils/i18n'

const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()

const activeTab = ref('profile')
const profileForm = ref({
  username: '',
  email: '',
  currentPassword: '',
  newPassword: '',
})

const savedEvents = ref([])
const followedCommunities = ref([])
const myComments = ref([])

const navItems = computed(() => [
  { id: 'profile', label: t('myProfile') },
  { id: 'saved', label: t('mySavedEvents') },
  { id: 'followed', label: t('myFollowedCommunities') },
  { id: 'comments', label: t('myComments') },
])

const formatTime = (date) => dateUtils.daysAgo(date)
const truncateText = (text, length = 80) => {
  if (!text) return ''
  return text.length > length ? `${text.substring(0, length)}...` : text
}

const loadData = async () => {
  try {
    const profileRes = await userService.getProfile()
    profileForm.value.username = profileRes.data.username
    profileForm.value.email = profileRes.data.email

    const savedRes = await userService.getSavedEvents()
    savedEvents.value = savedRes.data.events || []

    const followedRes = await userService.getFollowedCommunities()
    followedCommunities.value = followedRes.data.communities || []

    const commentsRes = await userService.getMyComments()
    myComments.value = commentsRes.data.comments || []
  } catch (error) {
    ElMessage.error('Failed to load data')
    console.error(error)
  }
}

const updateProfile = async () => {
  try {
    await userService.updateProfile({
      username: profileForm.value.username,
      email: profileForm.value.email,
      currentPassword: profileForm.value.currentPassword,
      newPassword: profileForm.value.newPassword || undefined,
    })
    ElMessage.success(t('profileUpdatedSuccessfully'))
    profileForm.value.currentPassword = ''
    profileForm.value.newPassword = ''
  } catch (error) {
    ElMessage.error(t('failedToUpdateProfile'))
  }
}

const removeSavedEvent = async (eventId) => {
  try {
    await eventService.unsaveEvent(eventId)
    savedEvents.value = savedEvents.value.filter((e) => e.id !== eventId)
    ElMessage.success(t('eventRemovedFromSaved'))
  } catch (error) {
    ElMessage.error(t('failedToRemoveEvent'))
  }
}

const unfollowCommunity = async (communityId) => {
  try {
    await communityService.unfollowCommunity(communityId)
    followedCommunities.value = followedCommunities.value.filter((c) => c.id !== communityId)
    ElMessage.success(t('communityUnfollowed'))
  } catch (error) {
    ElMessage.error(t('failedToUnfollow'))
  }
}

const deleteMyComment = async (commentId) => {
  try {
    const comment = myComments.value.find((c) => c.id === commentId)
    if (comment) {
      await commentService.deleteComment(comment.event_id || comment.eventId, commentId)
      myComments.value = myComments.value.filter((c) => c.id !== commentId)
      ElMessage.success(t('commentDeleted'))
    }
  } catch (error) {
    ElMessage.error(t('failedToDeleteCommentShort'))
  }
}

const goToEvent = (eventId) => {
  router.push(`/events/${eventId}`)
}

const goToCommunity = (communityId) => {
  router.push(`/communities/${communityId}`)
}

const logout = () => {
  userStore.logout()
  ElMessage.success(t('loggedOut'))
  router.push('/')
}

onMounted(() => {
  if (!userStore.isLoggedIn) {
    router.push('/auth')
    return
  }
  loadData()
})
</script>

<style scoped>
.user-center-page {
  background-color: var(--bg-color);
}

.dark-mode .user-center-page {
  background-color: transparent;
}

.sidebar {
  background-color: var(--surface-color);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
  padding: 20px;
  border-radius: 12px;
  height: fit-content;
}

.dark-mode .sidebar {
  background-color: var(--surface-color);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-item {
  padding: 10px 12px;
  border: none;
  background: none;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
  font-weight: 500;
}

.nav-item:hover {
  background-color: #f0f0f0;
}

.dark-mode .nav-item:hover {
  background-color: #333;
}

.nav-item.active {
  background-color: #409eff;
  color: white;
}

.main-content {
  background-color: var(--surface-color);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
  padding: 30px;
  border-radius: 12px;
}

.dark-mode .main-content {
  background-color: var(--surface-color);
}

.tab-content h2 {
  margin-bottom: 20px;
  font-size: 20px;
}

.profile-form {
  max-width: 500px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.dark-mode .form-group input {
  background-color: #333;
  border-color: #444;
  color: #fff;
}

.form-actions {
  display: flex;
  gap: 10px;
}

.form-actions .btn {
  flex: 1;
}

.events-list,
.communities-list,
.comments-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.event-item,
.community-item,
.comment-item {
  background-color: var(--surface-muted);
  padding: 15px;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.dark-mode .event-item,
.dark-mode .community-item,
.dark-mode .comment-item {
  background-color: var(--surface-muted);
}

.event-header,
.community-header,
.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.event-title,
.community-name {
  cursor: pointer;
  color: #409eff;
  margin: 0;
}

.event-title:hover,
.community-name:hover {
  text-decoration: underline;
}

.event-meta,
.community-meta,
.comment-date {
  font-size: 12px;
  color: #999;
}

.event-desc,
.comment-event {
  font-size: 13px;
  color: #666;
  margin: 8px 0;
}

.dark-mode .event-desc,
.dark-mode .comment-event {
  color: #aaa;
}

.comment-text {
  color: #333;
  line-height: 1.6;
}

.dark-mode .comment-text {
  color: #ccc;
}

.remove-btn,
.delete-btn {
  background: none;
  border: none;
  color: #f56c6c;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 8px;
}

.remove-btn:hover,
.delete-btn:hover {
  text-decoration: underline;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

@media (max-width: 768px) {
  .container {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }
}
</style>
