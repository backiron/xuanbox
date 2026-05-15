<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, ExternalLink, ShieldCheck } from 'lucide-vue-next'

import XbAssetIcon from '../../components/common/XbAssetIcon.vue'
import { setLocale } from '../../i18n'

const { t, locale } = useI18n()
const currentLocaleLabel = computed(() => locale.value === 'zh-CN' ? '中' : 'EN')
const localeTitle = computed(() => locale.value === 'zh-CN' ? t('common.language.switchToEnglish') : t('common.language.switchToChinese'))

function toggleLocale() {
  setLocale(locale.value === 'zh-CN' ? 'en' : 'zh-CN')
}
</script>

<template>
  <main class="xb-public-about-page">
    <section class="xb-public-about-card">
      <button class="xb-language-toggle xb-auth-language-toggle xb-about-language-toggle" type="button" :title="localeTitle" @click="toggleLocale">
        {{ currentLocaleLabel }}
      </button>

      <router-link class="xb-about-back" to="/login">
        <ArrowLeft :size="16" />
        {{ t('pages.aboutPublic.back') }}
      </router-link>

      <div class="xb-auth-logo">
        <XbAssetIcon name="logo" :size="42" />
        <span>XuanBox</span>
      </div>

      <h1>{{ t('pages.aboutPublic.title') }}</h1>
      <p>{{ t('pages.aboutPublic.intro') }}</p>

      <div class="xb-about-public-grid">
        <article>
          <ShieldCheck :size="20" />
          <h2>{{ t('pages.aboutPublic.openSourceTitle') }}</h2>
          <p>{{ t('pages.aboutPublic.openSourceText') }}</p>
        </article>
        <article>
          <ShieldCheck :size="20" />
          <h2>{{ t('pages.aboutPublic.commercialTitle') }}</h2>
          <p>{{ t('pages.aboutPublic.commercialText') }}</p>
        </article>
        <article>
          <ShieldCheck :size="20" />
          <h2>{{ t('pages.aboutPublic.securityTitle') }}</h2>
          <p>{{ t('pages.aboutPublic.securityText') }}</p>
        </article>
        <article>
          <ShieldCheck :size="20" />
          <h2>{{ t('pages.aboutPublic.brandTitle') }}</h2>
          <p>{{ t('pages.aboutPublic.brandText') }}</p>
        </article>
      </div>

      <div class="xb-auth-links">
        <a href="https://github.com/backiron/xuanbox" target="_blank" rel="noreferrer">
          {{ t('pages.aboutPublic.source') }}
          <ExternalLink :size="14" />
        </a>
        <a href="https://vianbeni.ca" target="_blank" rel="noreferrer">
          VIANBENI
          <ExternalLink :size="14" />
        </a>
        <a href="mailto:xuanbox@vianbeni.ca">xuanbox@vianbeni.ca</a>
      </div>
    </section>
  </main>
</template>
