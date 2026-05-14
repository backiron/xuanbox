import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  create,
  NButton,
  NCard,
  NConfigProvider,
  NDropdown,
  NInput,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NMessageProvider,
  NProgress,
  NSpace,
  NTag
} from 'naive-ui'

import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import './styles/variables.css'
import './styles/theme.css'
import './styles/layout.css'
import './styles/components.css'
import './styles/mobile.css'

const naive = create({
  components: [
    NButton,
    NCard,
    NConfigProvider,
    NDropdown,
    NInput,
    NLayout,
    NLayoutContent,
    NLayoutSider,
    NMessageProvider,
    NProgress,
    NSpace,
    NTag
  ]
})

const app = createApp(App)

app.use(createPinia())
app.use(i18n)
app.use(router)
app.use(naive)
app.mount('#app')
