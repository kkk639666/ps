import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/infer',
    name: 'infer',
    component: () => import('../views/InferView.vue'),
    meta: { title: '单张识别' }
  },
  {
    path: '/batch',
    name: 'batch',
    component: () => import('../views/BatchView.vue'),
    meta: { title: '批量识别' }
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/HistoryView.vue'),
    meta: { title: '历史记录' }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { title: '参数设置' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} — 番茄病虫害识别系统`
})

export default router
