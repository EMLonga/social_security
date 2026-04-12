<template>
  <header class="navbar" :class="{ 'dark-mode': isDark }">
    <div class="navbar-container">
      <div class="logo" @click="$router.push('/')">
        <span class="logo-text">{{ t('brandName') }}</span>
      </div>

      <nav class="nav-menu">
        <router-link to="/" class="nav-item">{{ t('home') }}</router-link>
        <router-link to="/events" class="nav-item">{{ t('events') }}</router-link>
        <router-link to="/communities" class="nav-item">{{ t('reports') }}</router-link>
        <router-link v-if="isLoggedIn && user" to="/user" class="nav-item">
          {{ t('myProfile') }}
        </router-link>
      </nav>

      <div class="navbar-right">
        <div class="search-box">
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('searchPlaceholder')"
            @keyup.enter="handleSearch"
          />
          <button @click="handleSearch" class="search-btn">{{ t('search') }}</button>
        </div>

        <button @click="toggleDarkMode" class="icon-btn" :title="t('themeToggle')">
          {{ isDark ? t('light') : t('dark') }}
        </button>

        <button @click="toggleLanguage" class="icon-btn" :title="t('languageToggle')">
          {{ language === 'en' ? t('langZhLabel') : 'English' }}
        </button>

        <div class="user-menu">
          <button v-if="!isLoggedIn" @click="goLogin" class="btn btn-primary">{{ t('login') }}</button>
          <div v-else class="user-profile">
            <el-dropdown @command="handleMenuCommand">
              <span class="user-name">{{ user?.username || t('user') }}</span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">{{ t('profile') }}</el-dropdown-item>
                  <el-dropdown-item v-if="user?.role === 'admin'" command="admin">
                    {{ t('adminPanel') }}
                  </el-dropdown-item>
                  <el-dropdown-item command="logout">{{ t('logout') }}</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore, useUserStore } from '../stores/app'
import { useI18n } from '../utils/i18n'

const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const { t } = useI18n()

const searchQuery = ref('')
const isDark = computed(() => appStore.isDarkMode)
const language = computed(() => appStore.language)
const isLoggedIn = computed(() => userStore.isLoggedIn)
const user = computed(() => userStore.user)

const toggleDarkMode = () => {
  appStore.setDarkMode(!isDark.value)
}

const toggleLanguage = () => {
  appStore.setLanguage(language.value === 'en' ? 'zh' : 'en')
}

const handleSearch = () => {
  if (!searchQuery.value.trim()) return
  router.push({
    name: 'EventList',
    query: { search: searchQuery.value.trim() },
  })
}

const goLogin = () => {
  router.push('/auth?mode=login')
}

const handleMenuCommand = (command) => {
  if (command === 'profile') {
    router.push('/user')
    return
  }
  if (command === 'admin') {
    router.push('/admin')
    return
  }
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success(t('loggedOutSuccessfully'))
    router.push('/')
  }
}
</script>

<style scoped>
.navbar {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  transition: background-color 0.3s, border-color 0.3s;
}

.navbar.dark-mode {
  background: rgba(12, 22, 38, 0.9);
  color: #e5e7eb;
  border-bottom: 1px solid #223149;
}

.navbar-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 70px;
}

.logo {
  font-size: 24px;
  font-weight: bold;
  cursor: pointer;
  white-space: nowrap;
  margin-right: 30px;
}

.logo-text {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-menu {
  display: flex;
  gap: 30px;
  flex: 1;
}

.nav-item {
  color: inherit;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s;
}

.nav-item:hover,
.nav-item.router-link-active {
  color: #409eff;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-box {
  display: flex;
  align-items: center;
  background-color: #eef3fb;
  border-radius: 999px;
  padding: 5px 10px;
  border: 1px solid #d9e4f4;
}

.navbar.dark-mode .search-box {
  background-color: #17253a;
  border-color: #2c4260;
}

.search-box input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  padding: 5px 10px;
  color: inherit;
}

.search-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: inherit;
}

.icon-btn {
  background: #eef3fb;
  border: 1px solid #d9e4f4;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  padding: 6px 10px;
  color: inherit;
}

.navbar.dark-mode .icon-btn {
  background: #17253a;
  border-color: #2c4260;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-primary {
  background-color: #409eff;
  color: white;
}

.btn-primary:hover {
  background-color: #66b1ff;
}

.user-menu {
  display: flex;
  align-items: center;
}

.user-name {
  cursor: pointer;
  color: inherit;
  font-weight: 500;
  padding: 6px 8px;
  border-radius: 8px;
}

.navbar.dark-mode .user-name:hover {
  background-color: #17253a;
}

@media (max-width: 768px) {
  .nav-menu {
    gap: 15px;
  }

  .search-box {
    display: none;
  }

  .navbar-right {
    gap: 10px;
  }
}
</style>
