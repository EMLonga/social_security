import axios from 'axios'
import { useUserStore } from '../stores/app'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

// Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
    }
    return Promise.reject(error)
  }
)

// Event APIs
const normalizeEventParams = (params = {}) => {
  return {
    page: params.page,
    page_size: params.page_size || params.pageSize || params.limit || 10,
    event_type: params.event_type || (typeof params.eventType === 'string' ? params.eventType : undefined),
    event_types: params.event_types || params.eventTypes || params.eventType,
    community: params.community,
    time_range: params.time_range || params.timeRange,
    danger_level: params.danger_level || params.dangerLevel,
    sort_by: params.sort_by || params.sortBy,
    sortOrder: params.sortOrder || params.sort_order || params.sort_order,
    search: params.search,
  }
}

const normalizeEvent = (event) => {
  if (!event) return event
  const communityName =
    event.community_name ??
    event.communityName ??
    (typeof event.community === 'object' ? event.community?.name : event.community)
  const communityId = event.community_id ?? event.communityId
  return {
    ...event,
    type: event.event_type ?? event.type,
    dangerLevel: event.danger_level ?? event.dangerLevel,
    likes: event.like_count ?? event.likes ?? 0,
    commentCount: event.comment_count ?? event.commentCount ?? 0,
    like_count: event.like_count ?? event.likes ?? 0,
    comment_count: event.comment_count ?? event.commentCount ?? 0,
    communityId,
    communityName,
    community: communityName || (communityId ? `Community #${communityId}` : 'Community'),
    eventTime: event.event_time ?? event.eventTime,
    createdAt: event.created_at ?? event.createdAt,
    latitude: event.latitude,
    longitude: event.longitude,
    dataSource: event.data_source ?? event.dataSource,
    source_url: event.source_url ?? event.sourceUrl,
  }
}

const normalizeEventList = (events) => (events || []).map(normalizeEvent)

export const eventService = {
  getEvents: async (params) => {
    const res = await apiClient.get('/events', { params: normalizeEventParams(params) })
    return {
      ...res,
      data: {
        ...res.data,
        events: normalizeEventList(res.data.events || []),
      },
    }
  },
  getEventById: async (id) => {
    const res = await apiClient.get(`/events/${id}`)
    return {
      ...res,
      data: {
        ...res.data,
        event: normalizeEvent(res.data),
      },
    }
  },
  createEvent: (data) => apiClient.post('/events', data),
  updateEvent: (id, data) => apiClient.put(`/events/${id}`, data),
  deleteEvent: (id) => apiClient.delete(`/events/${id}`),
  likeEvent: (id) => apiClient.post(`/events/${id}/like`),
  unlikeEvent: (id) => apiClient.delete(`/events/${id}/like`),
  saveEvent: (id) => apiClient.post(`/events/${id}/save`),
  unsaveEvent: (id) => apiClient.delete(`/events/${id}/save`),
}

// Community APIs
const normalizeCommunityParams = (params = {}) => {
  return {
    page: params.page,
    page_size: params.page_size || params.pageSize || params.limit || 10,
    state: params.state,
    city: params.city,
    search: params.search,
    sort_by: params.sort_by || params.sortBy,
    sortOrder: params.sortOrder || params.sort_order || 'desc',
  }
}

const normalizeCommunity = (community) => {
  if (!community) return community
  return {
    ...community,
    safetyScore: community.safety_score ?? community.safetyScore ?? 0,
    safetyLevel: community.safety_level ?? community.safetyLevel ?? 'medium',
    safety_score: community.safety_score ?? community.safetyScore ?? 0,
    safety_level: community.safety_level ?? community.safetyLevel ?? 'medium',
    report: community.report ?? {
      highRiskPeriods: 'N/A',
      highRiskLocations: 'N/A',
      safetyTips: 'N/A',
      yoyComparison: 'N/A',
    },
  }
}

const normalizeComment = (comment) => {
  if (!comment) return comment
  return {
    ...comment,
    createdAt: comment.created_at ?? comment.createdAt,
    eventId: comment.event_id ?? comment.eventId,
    userId: comment.user_id ?? comment.userId,
  }
}

const normalizeCommentList = (comments) => (comments || []).map(normalizeComment)

export const communityService = {
  getCommunities: async (params) => {
    const res = await apiClient.get('/communities', { params: normalizeCommunityParams(params) })
    return {
      ...res,
      data: {
        ...res.data,
        communities: (res.data.communities || []).map(normalizeCommunity),
      },
    }
  },
  getCommunityById: async (id) => {
    const res = await apiClient.get(`/communities/${id}`)
    return {
      ...res,
      data: {
        ...res.data,
        community: normalizeCommunity(res.data),
      },
    }
  },
  followCommunity: (id) => apiClient.post(`/communities/${id}/follow`),
  unfollowCommunity: (id) => apiClient.delete(`/communities/${id}/follow`),
}

// Comment APIs
export const commentService = {
  getComments: async (eventId, params) => {
    const res = await apiClient.get(`/events/${eventId}/comments`, { params })
    return {
      ...res,
      data: {
        ...res.data,
        comments: normalizeCommentList(res.data.comments || []),
      },
    }
  },
  createComment: (eventId, data) => apiClient.post(`/events/${eventId}/comments`, data),
  deleteComment: (eventId, commentId) => apiClient.delete(`/events/${eventId}/comments/${commentId}`),
}

// User APIs
export const userService = {
  getCaptcha: () => apiClient.get('/auth/captcha', { params: { _ts: Date.now() } }),
  login: (credentials) => apiClient.post('/auth/login', credentials),
  register: (data) => apiClient.post('/auth/register', data),
  sendPasswordResetCode: (data) => apiClient.post('/auth/password-reset/send-code', data),
  confirmPasswordReset: (data) => apiClient.post('/auth/password-reset/confirm', data),
  getProfile: () => apiClient.get('/users/profile'),
  updateProfile: (data) => apiClient.put('/users/profile', data),
  getSavedEvents: async () => {
    const res = await apiClient.get('/users/saved-events')
    return {
      ...res,
      data: {
        ...res.data,
        events: normalizeEventList(res.data.events || []),
      },
    }
  },
  getFollowedCommunities: async () => {
    const res = await apiClient.get('/users/followed-communities')
    return {
      ...res,
      data: {
        ...res.data,
        communities: (res.data.communities || []).map(normalizeCommunity),
      },
    }
  },
  getMyComments: async () => {
    const res = await apiClient.get('/users/comments')
    return {
      ...res,
      data: {
        ...res.data,
        comments: normalizeCommentList(res.data.comments || []),
      },
    }
  },
}

// Admin APIs
export const adminService = {
  getDashboard: () => apiClient.get('/admin/dashboard'),
  getEvents: (params) => apiClient.get('/admin/events', { params }),
  updateEvent: (id, data) => apiClient.put(`/admin/events/${id}`, data),
  deleteEvent: (id) => apiClient.delete(`/admin/events/${id}`),
  getCommunities: (params) => apiClient.get('/admin/communities', { params }),
  createCommunity: (data) => apiClient.post('/admin/communities', data),
  updateCommunity: (id, data) => apiClient.put(`/admin/communities/${id}`, data),
  deleteCommunity: (id) => apiClient.delete(`/admin/communities/${id}`),
  getComments: (params) => apiClient.get('/admin/comments', { params }),
  flagComment: (id) => apiClient.post(`/admin/comments/${id}/flag`),
  unflagComment: (id) => apiClient.post(`/admin/comments/${id}/unflag`),
  setCommentFlagStatus: async (id, is_flagged) => {
    try {
      return await apiClient.put(`/admin/comments/${id}/status`, { is_flagged })
    } catch (error) {
      // Backward-compatible fallback when backend hasn't reloaded new route yet.
      if (is_flagged) {
        return apiClient.post(`/admin/comments/${id}/flag`)
      }
      return apiClient.post(`/admin/comments/${id}/unflag`)
    }
  },
  deleteComment: (id) => apiClient.delete(`/admin/comments/${id}`),
  getUsers: (params) => apiClient.get('/admin/users', { params }),
  updateUserRole: (id, role) => apiClient.put(`/admin/users/${id}/role`, { role }),
  updateUserStatus: (id, is_active) => apiClient.put(`/admin/users/${id}/status`, { is_active }),
  deleteUser: (id) => apiClient.delete(`/admin/users/${id}`),
  getSpider: () => apiClient.get('/admin/spider'),
  triggerSpider: () => apiClient.post('/admin/spider/trigger'),
  stopSpider: () => apiClient.post('/admin/spider/stop'),
  getConfig: () => apiClient.get('/admin/config'),
  updateConfig: (data) => apiClient.put('/admin/config', data),
  addSensitiveWord: (word) => apiClient.post('/admin/sensitive-words', { word }),
  deleteSensitiveWord: (id) => apiClient.delete(`/admin/sensitive-words/${id}`),
}

// AI Assistant APIs
export const assistantService = {
  chat: (data) => apiClient.post('/assistant/chat', data),
}

export default apiClient
