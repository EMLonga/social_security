<template>
  <footer class="footer" :class="{ 'dark-mode': isDark }">
    <div class="footer-container">
      <div class="footer-section">
        <h4>{{ t('dataSourceTitle') }}</h4>
        <p>{{ t('footerDataSourceText') }}</p>
      </div>

      <div class="footer-section">
        <h4>{{ t('disclaimer') }}</h4>
        <p>{{ t('footerDisclaimerText') }}</p>
      </div>

      <div class="footer-section">
        <h4>{{ t('links') }}</h4>
        <ul>
          <li><a href="#" target="_blank">{{ t('privacyPolicy') }}</a></li>
          <li><a href="#" target="_blank">{{ t('termsOfService') }}</a></li>
          <li><a href="#" target="_blank">{{ t('contactUs') }}</a></li>
        </ul>
      </div>

      <div class="footer-section">
        <h4>{{ t('about') }}</h4>
        <p>&copy; 2026 {{ t('footerCopyright') }}</p>
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
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
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

.footer-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-section ul li {
  margin-bottom: 8px;
}

.footer-section a {
  color: #409eff;
  text-decoration: none;
  transition: color 0.3s;
}

.footer-section a:hover {
  color: #66b1ff;
}

</style>
