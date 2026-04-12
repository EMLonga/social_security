import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from './stores/app'

const routes = [
  {
    path: '/',
    component: () => import('./pages/Home.vue'),
    name: 'Home',
  },
  {
    path: '/events',
    component: () => import('./pages/EventList.vue'),
    name: 'EventList',
  },
  {
    path: '/events/:id',
    component: () => import('./pages/EventDetail.vue'),
    name: 'EventDetail',
  },
  {
    path: '/communities',
    component: () => import('./pages/CommunityList.vue'),
    name: 'CommunityList',
  },
  {
    path: '/communities/:id',
    component: () => import('./pages/CommunityDetail.vue'),
    name: 'CommunityDetail',
  },
  {
    path: '/auth',
    component: () => import('./pages/Auth.vue'),
    name: 'Auth',
  },
  {
    path: '/user',
    component: () => import('./pages/UserCenter.vue'),
    name: 'UserCenter',
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    component: () => import('./pages/admin/Dashboard.vue'),
    name: 'AdminDashboard',
    meta: { requiresAdmin: true },
  },
  {
    path: '/index.html',
    redirect: '/',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const userStore = useUserStore()

  if (to.meta?.requiresAuth && !userStore.isLoggedIn) {
    return { path: '/auth', query: { mode: 'login', redirect: to.fullPath } }
  }

  if (to.meta?.requiresAdmin) {
    if (!userStore.isLoggedIn) {
      return { path: '/auth', query: { mode: 'login', redirect: to.fullPath } }
    }
    if (userStore.user?.role !== 'admin') {
      return { path: '/' }
    }
  }

  return true
})

export default router
