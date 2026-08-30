import { createRouter, createWebHistory } from 'vue-router'
import AIScanView from '@/views/AIScanView.vue'
import NewMeasurementView from '@/views/NewMeasurementView.vue'
import OrderTrackingView from '@/views/OrderTrackingView.vue'
import AdminDashboard from '@/views/AdminDashboard.vue'

const routes = [
  {
    path: '/',
    redirect: '/scan',
  },
  {
    path: '/scan',
    name: 'scan',
    component: AIScanView,
  },
  {
    path: '/measurement',
    name: 'measurement',
    component: NewMeasurementView,
  },
  {
    path: '/tracking',
    name: 'tracking',
    component: OrderTrackingView,
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminDashboard,
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
