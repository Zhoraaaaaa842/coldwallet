import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Send from '@/views/Send.vue'
import Receive from '@/views/Receive.vue'
import SignBroadcast from '@/views/SignBroadcast.vue'
import Settings from '@/views/Settings.vue'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: Dashboard,
  },
  {
    path: '/send',
    name: 'send',
    component: Send,
  },
  {
    path: '/receive',
    name: 'receive',
    component: Receive,
  },
  {
    path: '/sign',
    name: 'sign',
    component: SignBroadcast,
  },
  {
    path: '/settings',
    name: 'settings',
    component: Settings,
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
