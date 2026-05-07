import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '../layouts/AppShell.vue'
import LoginView from '../views/auth/LoginView.vue'
import AdminDashboardView from '../views/admin/AdminDashboardView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'
import XuanDropView from '../views/drop/XuanDropView.vue'
import PublicDropView from '../views/drop/PublicDropView.vue'
import FilesView from '../views/files/FilesView.vue'
import PhotosView from '../views/photos/PhotosView.vue'
import ReceiptsView from '../views/receipts/ReceiptsView.vue'
import SettingsView from '../views/settings/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/drop/public/:token', component: PublicDropView, meta: { public: true } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        { path: 'photos', name: 'photos', component: PhotosView },
        { path: 'files', name: 'files', component: FilesView },
        { path: 'receipts', name: 'receipts', component: ReceiptsView },
        { path: 'drop', name: 'drop', component: XuanDropView },
        { path: 'settings', name: 'settings', component: SettingsView },
        { path: 'admin', name: 'admin', component: AdminDashboardView }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('xb_access_token')
  if (!token && to.path !== '/login' && !to.meta.public) return '/login'
})

export default router
