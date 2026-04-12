export const dateUtils = {
  getLocale: () => (localStorage.getItem('language') === 'zh' ? 'zh-CN' : 'en-US'),
  formatDate: (date) => {
    return new Date(date).toLocaleDateString(dateUtils.getLocale(), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  },
  formatTime: (date) => {
    return new Date(date).toLocaleTimeString(dateUtils.getLocale(), {
      hour: '2-digit',
      minute: '2-digit',
    })
  },
  formatDateTime: (date) => {
    return new Date(date).toLocaleString(dateUtils.getLocale())
  },
  daysAgo: (date) => {
    const isZh = localStorage.getItem('language') === 'zh'
    const ms = Date.now() - new Date(date).getTime()
    const days = Math.floor(ms / (1000 * 60 * 60 * 24))
    if (days === 0) return isZh ? '今天' : 'Today'
    if (days === 1) return isZh ? '昨天' : 'Yesterday'
    return isZh ? `${days} 天前` : `${days} days ago`
  },
}

export const eventTypeColors = {
  theft: '#1d4ed8', // Flood
  shooting: '#7c3aed', // Earthquake
  fire: '#dc2626', // Fire Risk
  security: '#0f766e', // General Alert
  fraud: '#f59e0b', // Severe Storm
  other: '#6b7280', // Other Hazard
}

export const dangerLevelColors = {
  low: '#67c23a',
  medium: '#e6a23c',
  high: '#f56c6c',
}

export const getEventTypeLabel = (type) => {
  const isZh = localStorage.getItem('language') === 'zh'
  const labels = isZh
    ? {
        theft: '洪水',
        shooting: '地震',
        fire: '火灾风险',
        security: '一般警报',
        fraud: '强风暴',
        other: '其他风险',
      }
    : {
        theft: 'Flood',
        shooting: 'Earthquake',
        fire: 'Fire Risk',
        security: 'General Alert',
        fraud: 'Severe Storm',
        other: 'Other Hazard',
      }
  return labels[type] || type
}

export const getDangerLevelLabel = (level) => {
  const isZh = localStorage.getItem('language') === 'zh'
  const labels = isZh
    ? {
        low: '低',
        medium: '中',
        high: '高',
      }
    : {
        low: 'Low',
        medium: 'Medium',
        high: 'High',
      }
  return labels[level] || level
}

export const getTrendLabel = (trend) => {
  const isZh = localStorage.getItem('language') === 'zh'
  if (trend === 'up') return isZh ? '上升' : 'UP'
  if (trend === 'down') return isZh ? '下降' : 'DOWN'
  return isZh ? '稳定' : 'STABLE'
}

export const getSafetyLevelLabel = (level) => {
  const isZh = localStorage.getItem('language') === 'zh'
  const labels = isZh
    ? {
        low: '低',
        medium: '中',
        high: '高',
      }
    : {
        low: 'LOW',
        medium: 'MEDIUM',
        high: 'HIGH',
      }
  const key = String(level || 'medium').toLowerCase()
  return labels[key] || labels.medium
}

export const mapNoDataLabel = () => (localStorage.getItem('language') === 'zh' ? '暂无数据' : 'No Data')

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

export const validatePassword = (password) => {
  return password.length >= 8 && /[a-zA-Z]/.test(password) && /[0-9]/.test(password)
}

export const validateUsername = (username) => {
  return username.length >= 6 && username.length <= 20
}
