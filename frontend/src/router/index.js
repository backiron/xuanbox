import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '../layouts/AppShell.vue'
import AdminLoginView from '../views/admin/AdminLoginView.vue'
import AboutPublicView from '../views/auth/AboutPublicView.vue'
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

const adminLoginMeta = { adminPublic: true, titleKey: 'pages.adminAuth.title' }

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/about', component: AboutPublicView, meta: { public: true } },
    { path: '/login', component: LoginView },
    { path: '/admin', component: AdminLoginView, meta: adminLoginMeta },
    { path: '/admin/login', redirect: '/admin' },
    { path: '/drop/public/:token', component: PublicDropView, meta: { public: true } },
    { path: '/public-share/:token', component: PublicShareView, meta: { public: true } },
    { path: '/admin-console', name: 'admin-console', component: AdminDashboardView, meta: { titleKey: 'routes.adminConsole', admin: true } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'dashboard', component: DashboardView, meta: { titleKey: 'routes.dashboard' } },
        { path: 'inbox', name: 'inbox', component: InboxView, meta: { titleKey: 'routes.inbox' } },
        { path: 'photos', name: 'photos', component: PhotosView, meta: { titleKey: 'routes.photos' } },
        { path: 'files', name: 'files', component: FilesView, meta: { titleKey: 'routes.files' } },
        { path: 'receipts', name: 'receipts', component: ReceiptsView, meta: { titleKey: 'routes.receipts' } },
        { path: 'drop', name: 'drop', component: XuanDropView, meta: { titleKey: 'routes.drop' } },
        { path: 'shared', name: 'shared', component: SharedView, meta: { titleKey: 'routes.shared' } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { titleKey: 'routes.settings' } },
        { path: 'messages', name: 'messages', component: MessagesView, meta: { titleKey: 'routes.messages' } },
        { path: 'search', name: 'search', component: SearchView, meta: { titleKey: 'routes.search' } }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('xb_access_token')
  const clientType = localStorage.getItem('xb_client_type')
  if (!token && to.path !== '/login' && !to.meta.public && !to.meta.adminPublic) return to.meta.admin ? '/admin' : '/login'
  if (to.meta.admin && clientType !== 'admin_console') return '/admin'
  if (token && !to.meta.admin && !to.meta.adminPublic && !to.meta.public && clientType === 'admin_console') return '/admin-console'
})

export default router
