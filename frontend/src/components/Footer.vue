<template>
  <footer class="footer" :class="{ 'dark-mode': isDark }">
    <div class="footer-container">
      <div class="footer-section">
        <h4>{{ t('about') }}</h4>
        <p>2026&#24180;&#21271;&#20140;&#20449;&#24687;&#31185;&#25216;&#22823;&#23398;&#29256;&#26435;&#25152;&#26377;</p>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import { useI18n } from '../utils/i18n'

const appStore = useAppStore()
const { t } = useI18n()
const isDark = computed(() => appStore.isDarkMode)
</script>

<style scoped>
.footer {
  background-color: rgba(255, 255, 255, 0.72);
  border-top: 1px solid #d7e1ef;
  backdrop-filter: blur(8px);
  margin-top: 50px;
  padding: 40px 20px;
  transition: background-color 0.3s;
}

.footer.dark-mode {
  background-color: rgba(12, 22, 38, 0.86);
  border-top-color: #25354d;
  color: #e5e7eb;
}

.footer-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.footer-section h4 {
  margin-bottom: 15px;
  font-weight: 600;
}

.footer-section p {
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.footer.dark-mode .footer-section p {
  color: #9fb0c8;
}
</style>
