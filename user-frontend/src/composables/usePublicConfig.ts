import { ref } from 'vue'
import { getPublicConfig, type PublicConfig } from '../api/cms'
import { applyFavicon } from '../utils/seo'

const config = ref<PublicConfig>({})
const loaded = ref(false)
let loading: Promise<void> | null = null

export function usePublicConfig() {
  async function load(force = false) {
    if (loaded.value && !force) return config.value
    if (!loading || force) {
      loading = getPublicConfig()
        .then((data) => {
          config.value = data
          loaded.value = true
          applyFavicon(data.favicon_url)
        })
        .catch(() => {
          config.value = {}
        })
    }
    await loading
    return config.value
  }

  return { config, loaded, load }
}
