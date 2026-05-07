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
import './styles/variables.css'
import './styles/theme.css'
import './styles/layout.css'
import './styles/mobile.css'
import './styles/components.css'

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

createApp(App).use(createPinia()).use(router).use(naive).mount('#app')
