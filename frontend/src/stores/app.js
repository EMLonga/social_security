import { defineStore } from 'pinia'
import { ref } from 'vue'
import Cookie from 'js-cookie'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(Cookie.get('token') || null)
  const isLoggedIn = ref(!!token.value)

  const login = (userData, authToken) => {
    user.value = userData
    token.value = authToken
    isLoggedIn.value = true
    Cookie.set('token', authToken, { expires: 7 })
  }

  const logout = () => {
    user.value = null
    token.value = null
    isLoggedIn.value = false
    Cookie.remove('token')
  }

  const updateUser = (userData) => {
    user.value = { ...(user.value || {}), ...userData }
    isLoggedIn.value = !!token.value
  }

  return {
    user,
    token,
    isLoggedIn,
    login,
    logout,
    updateUser,
  }
})

export const useAppStore = defineStore('app', () => {
  const isDarkMode = ref(localStorage.getItem('theme') === 'dark')
  const language = ref(localStorage.getItem('language') || 'en')

  const setDarkMode = (value) => {
    isDarkMode.value = value
    localStorage.setItem('theme', value ? 'dark' : 'light')
  }

  const setLanguage = (lang) => {
    language.value = lang
    localStorage.setItem('language', lang)
  }

  return {
    isDarkMode,
    language,
    setDarkMode,
    setLanguage,
  }
})

export const useFilterStore = defineStore('filter', () => {
  const filters = ref({
    eventType: [],
    community: null,
    city: null,
    state: null,
    timeRange: 'recent7days',
    dangerLevel: null,
    sortBy: 'publishTime',
  })

  const setFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const resetFilters = () => {
    filters.value = {
      eventType: [],
      community: null,
      city: null,
      state: null,
      timeRange: 'recent7days',
      dangerLevel: null,
      sortBy: 'publishTime',
    }
  }

  return {
    filters,
    setFilters,
    resetFilters,
  }
})
