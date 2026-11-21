import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import { usePublicConfig } from './composables/usePublicConfig'
import { applySeo, resolveRouteSeo } from './utils/seo'
import '@fortawesome/fontawesome-free/css/all.min.css'
import './style.css'
import './styles/admin.css'

async function bootstrap() {
  const { load, config } = usePublicConfig()
  await load().catch(() => undefined)

  const app = createApp(App)
  app.config.errorHandler = (err) => {
    if (axios.isAxiosError(err)) return
    const msg = String((err as Error)?.message || err)
    if (/Failed to fetch dynamically imported module|Loading chunk|access token expired/.test(msg)) return
    console.error(err)
  }
  app.use(createPinia())
  app.use(router)
  app.use(ElementPlus, { locale: zhCn })

  await router.isReady()
  applySeo(resolveRouteSeo(router.currentRoute.value, config.value))

  app.mount('#app')
}

bootstrap()
