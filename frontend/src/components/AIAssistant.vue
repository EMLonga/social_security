<template>
  <div ref="assistantRef" class="ai-assistant" :style="containerStyle">
    <transition name="fade">
      <div v-if="showFirstVisitTip && !isOpen" class="first-tip" @click="openPanel">
        <p>{{ ui.tip }}</p>
        <small>{{ ui.tipAction }}</small>
      </div>
    </transition>

    <button
      v-if="!isOpen"
      class="floating-btn"
      :class="{ pulse: showFirstVisitTip }"
      aria-label="AI Assistant"
      @mousedown.stop.prevent="startDrag($event)"
      @click="onFloatingButtonClick"
    >
      <span class="icon">✶</span>
      <span class="dot"></span>
    </button>

    <transition name="slide-up">
      <div v-if="isOpen" class="panel">
        <div class="panel-header" @mousedown.stop.prevent="startDrag($event)">
          <div>
            <h4>{{ ui.title }}</h4>
            <p>{{ roleText }}</p>
          </div>
          <div class="header-actions">
            <button class="head-btn" @click="resetPosition">{{ ui.resetPos }}</button>
            <button class="head-btn danger" @click="isOpen = false">{{ ui.close }}</button>
          </div>
        </div>

        <div class="page-hint">
          <strong>{{ currentGuide.title }}</strong>
          <span>{{ currentGuide.summary }}</span>
        </div>

        <div class="quick-questions">
          <button v-for="q in quickQuestions" :key="q" class="quick-btn" @click="askQuickQuestion(q)">
            {{ q }}
          </button>
        </div>

        <div ref="messagesRef" class="messages">
          <div v-for="msg in messages" :key="msg.id" class="msg" :class="msg.role">
            <div class="bubble">{{ msg.content }}</div>
          </div>
        </div>

        <div class="input-row">
          <input
            v-model="draft"
            class="input"
            :placeholder="ui.placeholder"
            :disabled="isReplying"
            @keydown.enter.prevent="sendMessage"
          />
          <button class="send-btn" :disabled="!draft.trim() || isReplying" @click="sendMessage">
            {{ isReplying ? ui.thinking : ui.send }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore, useUserStore } from '../stores/app'
import { assistantService } from '../services/api'

const appStore = useAppStore()
const userStore = useUserStore()
const route = useRoute()

const isZh = computed(() => appStore.language === 'zh')
const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => userStore.user?.role === 'admin')

const ui = computed(() =>
  isZh.value
    ? {
        title: 'AI 智能助手',
        close: '关闭',
        send: '发送',
        thinking: '思考中...',
        resetPos: '重置位置',
        placeholder: '输入问题，例如：这个页面的图表怎么看？',
        tip: '欢迎使用，我可以告诉你功能在哪、怎么用、数据什么意思。',
        tipAction: '点击打开',
      }
    : {
        title: 'AI Assistant',
        close: 'Close',
        send: 'Send',
        thinking: 'Thinking...',
        resetPos: 'Reset',
        placeholder: 'Ask: what does this chart mean?',
        tip: 'Welcome! I explain features, actions, and data in simple words.',
        tipAction: 'Click to open',
      }
)

const PAGE_GUIDES_ZH = {
  Home: {
    title: '首页',
    summary: '这里看全局地图、热门事件和 Top 5 社区。',
    questions: ['这页地图怎么看？', '热门事件和 Top 5 是什么意思？'],
    explain: [
      '地图点位表示事件发生位置，点越密说明该区域近期事件更集中。',
      '热门事件按热度排序，点击卡片进入事件详情。',
      'Top5 社区按安全评分排序，分数越高通常表示相对更安全。',
    ],
  },
  EventList: {
    title: '事件列表页',
    summary: '用于筛选和浏览全部事件。',
    questions: ['筛选项怎么用？', '事件卡片的关键字段怎么看？'],
    explain: [
      '筛选条件会缩小结果范围，先选类型再看时间范围更直观。',
      '每条事件可进入详情查看地图、来源、评论和收藏。',
    ],
  },
  EventDetail: {
    title: '事件详情页',
    summary: '这里能看事件位置、描述、评论、收藏和分享。',
    questions: ['详情页每个按钮是做什么的？', '危险等级是什么意思？'],
    explain: [
      'Like 表示点赞，Save 表示收藏，Share 用于复制链接。',
      '危险等级是该事件的风险提示，High 代表需要更谨慎。',
      '评论区用于补充现场信息，便于其他用户判断情况。',
    ],
  },
  CommunityList: {
    title: '社区列表页',
    summary: '用于对比不同社区安全情况。',
    questions: ['社区评分怎么理解？', '趋势上升/下降表示什么？'],
    explain: [
      '安全评分来自社区全部事件的自动计算结果。',
      '趋势上升通常表示风险缓和，趋势下降表示风险加重。',
    ],
  },
  CommunityDetail: {
    title: '社区详情页',
    summary: '这里有社区地图、图表和安全报告。',
    questions: ['饼图和折线图怎么看？', '报告四块内容是什么意思？'],
    explain: [
      '地图中蓝点是社区中心，彩色点是该社区事件分布。',
      '饼图看事件类型占比，折线图看最近一段时间变化。',
      '报告用于快速读出高风险时段、地点和防护建议。',
    ],
  },
  Auth: {
    title: '登录注册页',
    summary: '用于登录、注册和找回密码。',
    questions: ['忘记密码怎么操作？', '验证码失败怎么办？'],
    explain: [
      '忘记密码支持用户名或邮箱 + 图形验证码 + 邮箱验证码。',
      '邮箱验证码有效期为 5 分钟，发送后 30 秒内不可重复点击。',
    ],
  },
  UserCenter: {
    title: '个人中心',
    summary: '查看收藏、关注和个人互动记录。',
    questions: ['收藏和关注在哪看？', '我发的评论在哪找？'],
    explain: ['个人中心按模块集中展示你的收藏、关注和评论记录。'],
  },
  AdminDashboard: {
    title: '管理后台',
    summary: '管理员可管理事件、社区、评论、用户和抓取任务。',
    questions: ['后台模块分别做什么？', '抓取任务在哪里触发？'],
    explain: [
      '事件/社区/评论/用户模块用于数据维护和审核。',
      '抓取任务模块用于手动触发采集并检查执行状态。',
    ],
  },
  fallback: {
    title: '当前页面',
    summary: '你可以直接问我“这个按钮/图表/数据是什么意思”。',
    questions: ['这个页面怎么用？', '这块数据是什么意思？'],
    explain: ['告诉我你看到的文字，我会按页面位置一步步解释。'],
  },
}

const PAGE_GUIDES_EN = {
  Home: {
    title: 'Home',
    summary: 'Global map, hot events, and Top5 communities.',
    questions: ['How to read this map?', 'What are hot events and Top5?'],
    explain: [
      'Markers show incident locations; dense areas mean clustered recent incidents.',
      'Hot events are sorted by popularity; click a card for detail.',
      'Top5 communities are ranked by safety score.',
    ],
  },
  EventList: {
    title: 'Events',
    summary: 'Filter and browse all events.',
    questions: ['How to use filters?', 'How to read event cards?'],
    explain: [
      'Use type + time filters to narrow results quickly.',
      'Open detail to see map, source, comments, and save action.',
    ],
  },
  EventDetail: {
    title: 'Event Detail',
    summary: 'Map, description, comments, save and share actions.',
    questions: ['What does each button do?', 'What does danger level mean?'],
    explain: [
      'Like = support, Save = bookmark, Share = copy link.',
      'Danger level is a risk hint for this event.',
      'Comments add local context for other users.',
    ],
  },
  CommunityList: {
    title: 'Communities',
    summary: 'Compare safety across communities.',
    questions: ['How to understand safety score?', 'What does trend mean?'],
    explain: [
      'Safety score is automatically calculated from all events in the community.',
      'Trend up/down indicates recent risk improving or worsening.',
    ],
  },
  CommunityDetail: {
    title: 'Community Detail',
    summary: 'Map, charts, and community safety report.',
    questions: ['How to read pie and line chart?', 'What does report mean?'],
    explain: [
      'Blue marker is the community center; color markers are event points.',
      'Pie chart shows event type share; line chart shows trend over time.',
      'Report summarizes risk periods, locations, and safety tips.',
    ],
  },
  Auth: {
    title: 'Auth',
    summary: 'Login, register, and password reset.',
    questions: ['How does forgot password work?', 'Why does captcha fail?'],
    explain: [
      'Reset uses username/email + image captcha + email code.',
      'Email code is valid for 5 minutes; resend cooldown is 30 seconds.',
    ],
  },
  UserCenter: {
    title: 'User Center',
    summary: 'Saved items, follows, and your interactions.',
    questions: ['Where are saved items?', 'Where are my comments?'],
    explain: ['This page groups your saved/followed/comment history.'],
  },
  AdminDashboard: {
    title: 'Admin Panel',
    summary: 'Manage events, communities, comments, users, spider tasks.',
    questions: ['What does each module do?', 'Where to trigger spider task?'],
    explain: ['Use module tabs for maintenance and spider execution.'],
  },
  fallback: {
    title: 'Current Page',
    summary: 'Ask me about any button/chart/metric on this page.',
    questions: ['How to use this page?', 'What does this data mean?'],
    explain: ['Tell me the label you see and I will explain it step by step.'],
  },
}

const roleText = computed(() => {
  if (isZh.value) {
    if (isAdmin.value) return '管理员：通用功能 + 后台功能引导'
    if (isLoggedIn.value) return '登录用户：通用功能引导'
    return '访客：通用功能引导'
  }
  if (isAdmin.value) return 'Admin: general + admin guidance'
  if (isLoggedIn.value) return 'User: general guidance'
  return 'Guest: general guidance'
})

const currentGuide = computed(() => {
  const map = isZh.value ? PAGE_GUIDES_ZH : PAGE_GUIDES_EN
  const key = route.name || 'fallback'
  if (key === 'AdminDashboard' && !isAdmin.value) return map.fallback
  return map[key] || map.fallback
})

const quickQuestions = computed(() => {
  const common = isZh.value
    ? ['首页怎么看全局信息？', '安全指数怎么理解？', '这个页面按钮有什么用？']
    : ['How to use Home quickly?', 'How to read safety score?', 'What do buttons on this page do?']
  const merged = [...(currentGuide.value.questions || []), ...common]
  return [...new Set(merged)].slice(0, 3)
})

const FIRST_VISIT_KEY = 'ai_assistant_first_tip_seen_v3'
const INTRO_DONE_KEY = 'ai_assistant_intro_done_v3'
const POS_KEY = 'ai_assistant_pos_v3'

const isOpen = ref(false)
const showFirstVisitTip = ref(false)
const draft = ref('')
const isReplying = ref(false)
const messages = ref([])
const messagesRef = ref(null)

const position = ref({ x: 0, y: 0 })
const assistantRef = ref(null)
const dragging = ref(false)
const dragStartPoint = ref({ x: 0, y: 0 })
const dragOffset = ref({ x: 0, y: 0 })
const dragMoved = ref(false)
const ignoreNextClick = ref(false)

let resizeHandler = null

const containerStyle = computed(() => ({
  left: `${position.value.x}px`,
  top: `${position.value.y}px`,
}))

const getPanelSize = () => {
  const h = Math.round(window.innerHeight * 0.66)
  return {
    width: Math.min(380, window.innerWidth - 24),
    height: Math.max(420, Math.min(560, h)),
  }
}

const clampPosition = (x, y) => {
  const pad = 8
  const btnW = 62
  const btnH = 62
  const panel = getPanelSize()

  const minX = isOpen.value ? Math.max(pad, panel.width - btnW + pad) : pad
  const maxX = Math.max(minX, window.innerWidth - btnW - pad)

  const minY = isOpen.value ? Math.max(pad, panel.height + 18 + pad) : pad
  const maxY = Math.max(minY, window.innerHeight - btnH - pad)

  return {
    x: Math.max(minX, Math.min(maxX, x)),
    y: Math.max(minY, Math.min(maxY, y)),
  }
}

const savePosition = () => {
  localStorage.setItem(POS_KEY, JSON.stringify(position.value))
}

const resetPosition = () => {
  position.value = clampPosition(window.innerWidth - 96, window.innerHeight - 128)
  savePosition()
}

const onDragMove = (e) => {
  if (!dragging.value) return
  const movedX = Math.abs(e.clientX - dragStartPoint.value.x)
  const movedY = Math.abs(e.clientY - dragStartPoint.value.y)
  if (movedX > 4 || movedY > 4) dragMoved.value = true
  position.value = clampPosition(e.clientX - dragOffset.value.x, e.clientY - dragOffset.value.y)
}

const onDragEnd = () => {
  if (!dragging.value) return
  dragging.value = false
  savePosition()
  if (dragMoved.value) {
    ignoreNextClick.value = true
    setTimeout(() => {
      ignoreNextClick.value = false
    }, 180)
  }
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}

const startDrag = (e) => {
  const rect = assistantRef.value?.getBoundingClientRect?.() || e.currentTarget.getBoundingClientRect()
  dragging.value = true
  dragMoved.value = false
  dragStartPoint.value = { x: e.clientX, y: e.clientY }
  dragOffset.value = { x: e.clientX - rect.left, y: e.clientY - rect.top }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

const pushMessage = (role, content) => {
  messages.value.push({ id: `${Date.now()}_${Math.random()}`, role, content })
}

const buildIntro = () => {
  if (isZh.value) {
    let text = '你好，我是网站 AI 助手。这个网站用来查看社区安全事件、地图分布和趋势变化。'
    text += '\n你可以从首页进入事件和社区详情；我可以随时解释图表、指标、按钮和专业名词。'
    if (isAdmin.value) {
      text += '\n你当前是管理员，还可以在后台管理数据并触发抓取任务。'
    }
    return text
  }

  let text = 'Hi, I am your AI assistant. This site shows community safety using incidents, maps, and trends.'
  text += '\nYou can start from Home and open event/community details; I can explain charts, metrics, buttons, and terms.'
  if (isAdmin.value) {
    text += '\nAs admin, you can also manage data and trigger spider tasks in Admin Panel.'
  }
  return text
}

const buildPageExplanation = () => {
  const lines = [currentGuide.value.summary, ...(currentGuide.value.explain || [])]
  return lines.join('\n')
}

const buildGlossaryReply = (input) => {
  const text = input.toLowerCase()
  const zh = isZh.value

  if (text.includes('安全指数') || text.includes('安全评分') || text.includes('safety score') || text.includes('index')) {
    return zh
      ? '安全指数可以理解为“社区近期风险体温计”：分数越高通常代表相对更安全。它会根据该社区全部事件自动计算并定时重算。'
      : 'Safety score is a risk thermometer for the community. Higher usually means relatively safer, and it is auto-calculated from all events.'
  }
  if (text.includes('趋势') || text.includes('trend')) {
    return zh
      ? '趋势看的是“变化方向”：上升通常代表风险在缓和，下降通常代表风险在加重。'
      : 'Trend shows direction of change: up usually means improving risk, down usually means worsening.'
  }
  if (text.includes('饼图') || text.includes('pie')) {
    return zh
      ? '饼图看“占比”：哪类事件最多一眼能看出来。'
      : 'Pie chart shows proportion, so you can see which event type dominates.'
  }
  if (text.includes('折线') || text.includes('line chart') || text.includes('曲线')) {
    return zh
      ? '折线图看“时间变化”：线往上说明该时段事件数量更多。'
      : 'Line chart shows change over time; higher line means more incidents in that period.'
  }
  if (text.includes('地图') || text.includes('marker') || text.includes('点位')) {
    return zh
      ? '地图点位代表事件发生位置。点位密集通常表示该区域近期事件更集中。'
      : 'Map markers represent incident locations. Dense markers usually mean clustered incidents.'
  }
  return ''
}

const buildReply = (question) => {
  const raw = String(question || '')
  const input = raw.toLowerCase()
  const has = (arr) => arr.some((k) => input.includes(k))

  const explainCurrentPage = has([
    '这个页面',
    '这页',
    '这里',
    '看不懂',
    '什么意思',
    '怎么理解',
    'button',
    'chart',
    'data',
    'term',
    'this page',
    'what is this',
    'what does this',
  ])

  if (explainCurrentPage) {
    return buildPageExplanation()
  }

  const glossary = buildGlossaryReply(raw)
  if (glossary) return glossary

  if (has(['hot', '热门', 'home', '首页', '事件'])) {
    return isZh.value
      ? '进入“首页”后，地图下方左侧是热门事件区，点击事件卡片可进入详情页。'
      : 'Open Home from navbar. Hot events are under the map on the left.'
  }

  if (has(['community', '社区', 'top', 'top5'])) {
    return isZh.value
      ? '你可以从“社区”页进入，或在首页 Top5 社区区域直接点击社区名称查看详情。'
      : 'Use Communities page or click Top5 items on Home.'
  }

  if (has(['save', 'comment', 'like', '收藏', '评论', '点赞'])) {
    return isZh.value
      ? '先登录，再进入事件详情页。描述区下方可点赞/收藏/分享，继续往下是评论区。'
      : 'Login first, open Event Detail, then use like/save/share and the comments area.'
  }

  if (has(['reset', 'forgot', 'password', '找回', '密码'])) {
    return isZh.value
      ? '登录页点击“忘记密码”，输入用户名或邮箱 + 图形验证码，发送邮箱验证码后填写新密码即可。'
      : 'Use Forgot Password on Auth page: username/email + captcha + email code, then set new password.'
  }

  if (has(['admin', '后台', '管理'])) {
    if (!isAdmin.value) {
      return isZh.value ? '后台功能仅管理员可用。' : 'Admin features require admin login.'
    }
    return isZh.value
      ? '管理员可在顶部导航进入管理后台，进行事件、社区、评论、用户与抓取任务管理。'
      : 'Admins can open Admin Panel from navbar to manage events/communities/comments/users/spider tasks.'
  }

  return isZh.value
    ? '你可以直接问我这页任意元素，比如“这个图表怎么读”“这个按钮做什么”“这个指标代表什么”。'
    : 'Ask me about any element on this page, like chart meaning, button action, or metric definition.'
}

const currentRole = computed(() => {
  if (isAdmin.value) return 'admin'
  if (isLoggedIn.value) return 'user'
  return 'guest'
})

const generateAssistantReply = async (question) => {
  try {
    const response = await assistantService.chat({
      message: question,
      language: isZh.value ? 'zh' : 'en',
      page_name: String(route.name || 'unknown'),
      page_path: route.path,
      role: currentRole.value,
      page_summary: currentGuide.value.summary,
      page_explain: currentGuide.value.explain || [],
    })
    const reply = response?.data?.reply
    if (typeof reply === 'string' && reply.trim()) {
      return reply.trim()
    }
  } catch (error) {
    console.error('assistant api failed, fallback to local reply', error?.response?.data || error)
  }
  return buildReply(question)
}

const scrollToBottom = async () => {
  await nextTick()
  const el = messagesRef.value
  if (el) el.scrollTop = el.scrollHeight
}

const maybeSendIntroOnce = () => {
  const introDone = localStorage.getItem(INTRO_DONE_KEY) === '1'
  if (introDone) return
  pushMessage('assistant', buildIntro())
  localStorage.setItem(INTRO_DONE_KEY, '1')
}

const openPanel = async () => {
  isOpen.value = true
  showFirstVisitTip.value = false
  maybeSendIntroOnce()
  await scrollToBottom()
}

const togglePanel = async () => {
  if (isOpen.value) {
    isOpen.value = false
    return
  }
  await openPanel()
}

const onFloatingButtonClick = async () => {
  if (ignoreNextClick.value) return
  await togglePanel()
}

const sendMessage = async () => {
  const content = draft.value.trim()
  if (!content || isReplying.value) return
  pushMessage('user', content)
  draft.value = ''
  isReplying.value = true
  const reply = await generateAssistantReply(content)
  pushMessage('assistant', reply)
  isReplying.value = false
  await scrollToBottom()
}

const askQuickQuestion = async (q) => {
  if (isReplying.value) return
  pushMessage('user', q)
  isReplying.value = true
  const reply = await generateAssistantReply(q)
  pushMessage('assistant', reply)
  isReplying.value = false
  await scrollToBottom()
}

onMounted(() => {
  const storedPos = localStorage.getItem(POS_KEY)
  if (storedPos) {
    try {
      const parsed = JSON.parse(storedPos)
      position.value = clampPosition(Number(parsed.x) || 0, Number(parsed.y) || 0)
    } catch {
      resetPosition()
    }
  } else {
    resetPosition()
  }

  const seen = localStorage.getItem(FIRST_VISIT_KEY)
  if (!seen) {
    showFirstVisitTip.value = true
    localStorage.setItem(FIRST_VISIT_KEY, '1')
    setTimeout(() => {
      showFirstVisitTip.value = false
    }, 10000)
  }

  resizeHandler = () => {
    position.value = clampPosition(position.value.x, position.value.y)
    savePosition()
  }
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  onDragEnd()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})
</script>

<style scoped>
.ai-assistant {
  position: fixed;
  z-index: 3100;
}

.floating-btn {
  width: 62px;
  height: 62px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 50%;
  background:
    radial-gradient(80px 48px at 18% 12%, rgba(255, 255, 255, 0.42), transparent 68%),
    linear-gradient(145deg, #8b5cf6 0%, #3b82f6 68%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.36);
  cursor: pointer;
  position: relative;
  backdrop-filter: blur(8px);
}

.icon {
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  text-shadow: 0 2px 10px rgba(255, 255, 255, 0.34);
}

.dot {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.85);
}

.pulse {
  animation: pulse 1.9s ease-in-out infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(29, 78, 216, 0.45);
  }
  70% {
    box-shadow: 0 0 0 16px rgba(29, 78, 216, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(29, 78, 216, 0);
  }
}

.first-tip {
  position: absolute;
  right: 0;
  bottom: 72px;
  width: 286px;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: #fff;
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.16);
  padding: 11px 12px;
  cursor: pointer;
}

.first-tip p {
  margin: 0 0 4px;
  font-size: 13px;
  color: #0f172a;
  line-height: 1.5;
}

.first-tip small {
  color: #2563eb;
  font-weight: 700;
}

.panel {
  position: absolute;
  right: 0;
  top: 0;
  transform: translateY(calc(-100% - 12px));
  width: 380px;
  height: 66vh;
  max-height: 560px;
  min-height: 420px;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background:
    radial-gradient(280px 120px at 15% 0%, rgba(14, 165, 233, 0.12), transparent 70%),
    var(--surface-color);
  box-shadow: 0 22px 42px rgba(15, 23, 42, 0.24);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  cursor: move;
}

.panel-header h4 {
  margin: 0;
  font-size: 15px;
}

.panel-header p {
  margin: 4px 0 0;
  color: var(--text-color-light);
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 6px;
}

.head-btn {
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-color);
}

.head-btn.danger {
  color: #dc2626;
}

.page-hint {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: rgba(148, 163, 184, 0.12);
  border-bottom: 1px solid var(--border-color);
  font-size: 11px;
}

.page-hint strong {
  color: var(--text-color);
}

.page-hint span {
  color: var(--text-color-light);
  opacity: 0.9;
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
}

.quick-btn {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
}

.messages {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.msg {
  display: flex;
}

.msg.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 90%;
  padding: 8px 10px;
  border-radius: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg.assistant .bubble {
  background: var(--surface-muted);
  border: 1px solid var(--border-color);
  color: var(--text-color);
}

.msg.user .bubble {
  background: #2563eb;
  color: #fff;
}

.input-row {
  border-top: 1px solid var(--border-color);
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.input {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 8px 10px;
  background: var(--surface-color);
  color: var(--text-color);
}

.send-btn {
  border: none;
  border-radius: 10px;
  padding: 0 13px;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
  color: #fff;
  cursor: pointer;
}

.send-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.22s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}

@media (max-width: 768px) {
  .panel {
    width: min(90vw, 380px);
    height: 62vh;
    min-height: 360px;
  }

  .first-tip {
    width: min(82vw, 286px);
  }
}
</style>
