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
  theft: '#1d4ed8',
  shooting: '#7c3aed',
  fire: '#dc2626',
  security: '#0f766e',
  fraud: '#f59e0b',
  other: '#6b7280',
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
        theft: '盗窃/财产案件',
        shooting: '暴力案件',
        fire: '火灾/纵火',
        security: '公共安全警情',
        fraud: '诈骗/欺诈',
        other: '其他',
      }
    : {
        theft: 'Theft / Property Crime',
        shooting: 'Violent Crime',
        fire: 'Fire / Arson',
        security: 'Public Safety Alert',
        fraud: 'Fraud / Scam',
        other: 'Other',
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
