import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '../layouts/AppShell.vue'
import AdminLoginView from '../views/admin/AdminLoginView.vue'
import LoginView from '../views/auth/LoginView.vue'
import AdminDashboardView from '../views/admin/AdminDashboardView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'
import InboxView from '../views/inbox/InboxView.vue'
import XuanDropView from '../views/drop/XuanDropView.vue'
import PublicDropView from '../views/drop/PublicDropView.vue'
import FilesView from '../views/files/FilesView.vue'
import PhotosView from '../views/photos/PhotosView.vue'
import ReceiptsView from '../views/receipts/ReceiptsView.vue'
import PublicShareView from '../views/shared/PublicShareView.vue'
import SharedView from '../views/shared/SharedView.vue'
import SettingsView from '../views/settings/SettingsView.vue'
import SearchView from '../views/search/SearchView.vue'
import MessagesView from '../views/messages/MessagesView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/admin/login', component: AdminLoginView, meta: { adminPublic: true } },
    { path: '/drop/public/:token', component: PublicDropView, meta: { public: true } },
    { path: '/public-share/:token', component: PublicShareView, meta: { public: true } },
    { path: '/admin-console', name: 'admin-console', component: AdminDashboardView, meta: { title: 'Admin Console', admin: true } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'dashboard', component: DashboardView, meta: { title: 'Dashboard' } },
        { path: 'inbox', name: 'inbox', component: InboxView, meta: { title: 'Inbox' } },
        { path: 'photos', name: 'photos', component: PhotosView, meta: { title: 'Photos' } },
        { path: 'files', name: 'files', component: FilesView, meta: { title: 'Files' } },
        { path: 'receipts', name: 'receipts', component: ReceiptsView, meta: { title: 'Receipts' } },
        { path: 'drop', name: 'drop', component: XuanDropView, meta: { title: 'XuanDrop' } },
        { path: 'shared', name: 'shared', component: SharedView, meta: { title: 'Shared' } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { title: 'Settings' } },
        { path: 'messages', name: 'messages', component: MessagesView, meta: { title: 'Messages' } },
        { path: 'search', name: 'search', component: SearchView, meta: { title: 'Search' } }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('xb_access_token')
  const clientType = localStorage.getItem('xb_client_type')
  if (!token && to.path !== '/login' && !to.meta.public && !to.meta.adminPublic) return to.meta.admin ? '/admin/login' : '/login'
  if (to.meta.admin && clientType !== 'admin_console') return '/admin/login'
  if (token && !to.meta.admin && !to.meta.adminPublic && !to.meta.public && clientType === 'admin_console') return '/admin-console'
})

export default router
