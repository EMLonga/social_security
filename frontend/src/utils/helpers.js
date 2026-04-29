import cityZhMap from '../data/city_zh_map.json'

export const dateUtils = {
  getLocale: () => (localStorage.getItem('language') === 'zh' ? 'zh-CN' : 'en-US'),
  formatDate: (date) =>
    new Date(date).toLocaleDateString(dateUtils.getLocale(), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }),
  formatTime: (date) =>
    new Date(date).toLocaleTimeString(dateUtils.getLocale(), {
      hour: '2-digit',
      minute: '2-digit',
    }),
  formatDateTime: (date) => new Date(date).toLocaleString(dateUtils.getLocale()),
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
  earthquake: '#0ea5e9',
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
        earthquake: '地震',
        other: '其他',
      }
    : {
        theft: 'Theft / Property Crime',
        shooting: 'Violent Crime',
        fire: 'Fire / Arson',
        security: 'Public Safety Alert',
        fraud: 'Fraud / Scam',
        earthquake: 'Earthquake',
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

export const validatePassword = (password) => password.length >= 8 && /[a-zA-Z]/.test(password) && /[0-9]/.test(password)

export const validateUsername = (username) => username.length >= 6 && username.length <= 20

const US_STATE_ZH = {
  AL: '阿拉巴马州', AK: '阿拉斯加州', AZ: '亚利桑那州', AR: '阿肯色州', CA: '加利福尼亚州',
  CO: '科罗拉多州', CT: '康涅狄格州', DE: '特拉华州', FL: '佛罗里达州', GA: '佐治亚州',
  HI: '夏威夷州', ID: '爱达荷州', IL: '伊利诺伊州', IN: '印第安纳州', IA: '艾奥瓦州',
  KS: '堪萨斯州', KY: '肯塔基州', LA: '路易斯安那州', ME: '缅因州', MD: '马里兰州',
  MA: '马萨诸塞州', MI: '密歇根州', MN: '明尼苏达州', MS: '密西西比州', MO: '密苏里州',
  MT: '蒙大拿州', NE: '内布拉斯加州', NV: '内华达州', NH: '新罕布什尔州', NJ: '新泽西州',
  NM: '新墨西哥州', NY: '纽约州', NC: '北卡罗来纳州', ND: '北达科他州', OH: '俄亥俄州',
  OK: '俄克拉何马州', OR: '俄勒冈州', PA: '宾夕法尼亚州', RI: '罗得岛州', SC: '南卡罗来纳州',
  SD: '南达科他州', TN: '田纳西州', TX: '得克萨斯州', UT: '犹他州', VT: '佛蒙特州',
  VA: '弗吉尼亚州', WA: '华盛顿州', WV: '西弗吉尼亚州', WI: '威斯康星州', WY: '怀俄明州',
  DC: '哥伦比亚特区', PR: '波多黎各',
}

const PLACE_TOKEN_ZH = {
  River: '河',
  Lake: '湖',
  Valley: '谷',
  Springs: '泉',
  Spring: '泉',
  Point: '角',
  Port: '港',
  Harbor: '港',
  Village: '村',
  City: '市',
  Falls: '瀑布',
  Mountain: '山',
  Mountains: '群山',
  Park: '公园',
  Road: '路',
  Creek: '溪',
  Ridge: '岭',
  Bay: '湾',
  Air: '航空',
  Force: '部队',
  Base: '基地',
  Observatory: '天文台',
  National: '国家',
  Fire: '火情',
  Wildfire: '野火',
  Prescribed: '计划',
}

const autoTranslatePlace = (place) => {
  const text = String(place || '').trim()
  if (!text) return ''
  const parts = text.split(/[\s\-]+/).filter(Boolean)
  const mapped = parts.map((p) => PLACE_TOKEN_ZH[p] || p)
  return mapped.join('')
}

export const localizeCommunityName = (name, state, city) => {
  const isZh = localStorage.getItem('language') === 'zh'
  if (!isZh) return name || city || ''
  const st = String(state || '').trim().toUpperCase()
  const stateZh = US_STATE_ZH[st] || st
  const ct = String(city || '').trim()
  // Pattern: "11 km NE of X" => "距X东北11公里"
  const distanceMatch = ct.match(/^(\d+(?:\.\d+)?)\s*km\s+([A-Z]{1,4})\s+of\s+(.+)$/i)
  if (distanceMatch) {
    const km = distanceMatch[1]
    const dirCode = distanceMatch[2].toUpperCase()
    const target = distanceMatch[3].trim()
    const dirMap = {
      N: '北', S: '南', E: '东', W: '西',
      NE: '东北', NW: '西北', SE: '东南', SW: '西南',
      NNE: '东北偏北', NNW: '西北偏北', ENE: '东北偏东', ESE: '东南偏东',
      SSE: '东南偏南', SSW: '西南偏南', WNW: '西北偏西', WSW: '西南偏西',
    }
    const targetZh = cityZhMap[target] || autoTranslatePlace(target) || target
    return `距${targetZh}${dirMap[dirCode] || dirCode}${km}公里（${stateZh}）`
  }
  let cityZh = cityZhMap[ct] || ''
  if (!cityZh) cityZh = autoTranslatePlace(ct)
  // Guardrail: community label must include city identity; never degrade to pure state label.
  if (cityZh && cityZh === stateZh) cityZh = ''
  const cityLabel = cityZh || ct
  if (cityLabel && stateZh) return `${cityLabel}（${stateZh}）`
  if (ct) return ct
  return name || ''
}
