<template>
  <div id="app" class="app" :class="{ 'dark-mode': isDark }">
    <Navbar />
    <div class="main-content">
      <RouterView />
    </div>
    <Footer />
    <AIAssistant />
  </div>
</template>

<script setup>
import { computed, watchEffect } from 'vue'
import { RouterView } from 'vue-router'
import Navbar from './components/Navbar.vue'
import Footer from './components/Footer.vue'
import AIAssistant from './components/AIAssistant.vue'
import { useAppStore } from './stores/app'

const appStore = useAppStore()
const isDark = computed(() => appStore.isDarkMode)

watchEffect(() => {
  document.body.classList.toggle('dark-mode', isDark.value)
})
</script>

<style scoped>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  color: var(--text-color);
  transition: background-color 0.3s, color 0.3s;
}

.main-content {
  flex: 1;
  width: 100%;
}

#app.dark-mode {
  background: transparent;
  color: var(--text-color);
}
</style>
