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
import './styles/drop.css'
import './styles/vault.css'

// Page-view analytics stay off unless whoever builds this install turns them on.
const analyticsSrc = import.meta.env.VITE_ANALYTICS_SRC
const analyticsSite = import.meta.env.VITE_ANALYTICS_SITE
if (analyticsSrc && analyticsSite) {
  const script = document.createElement('script')
  script.async = true
  script.src = analyticsSrc
  script.dataset.site = analyticsSite
  document.head.appendChild(script)
}

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
