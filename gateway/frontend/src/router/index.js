import { createRouter, createWebHistory } from 'vue-router'
import SubmitPage from '../views/SubmitPage.vue'
import HistoryPage from '../views/HistoryPage.vue'

const routes = [
  { path: '/', redirect: '/submit' },
  { path: '/submit', component: SubmitPage, meta: { title: '推理提交' } },
  { path: '/history', component: HistoryPage, meta: { title: '历史记录' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '推理网关'} - 推理网关`
})

export default router