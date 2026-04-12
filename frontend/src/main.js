import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'leaflet/dist/leaflet.css'

import App from './App.vue'
import router from './router'
import './styles/main.css'
import { useUserStore, useAppStore } from './stores/app'
import { userService } from './services/api'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

const bootstrap = async () => {
  const appStore = useAppStore()
  const userStore = useUserStore()

  document.body.classList.toggle('dark-mode', appStore.isDarkMode)

  if (userStore.token && !userStore.user) {
    try {
      const res = await userService.getProfile()
      userStore.updateUser(res.data)
    } catch {
      userStore.logout()
    }
  }
}

bootstrap().finally(() => {
  app.mount('#app')
})
