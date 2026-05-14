<script setup>
import dashboard from '../../assets/xuanbox-icons/icon_01_dashboard.svg'
import photos from '../../assets/xuanbox-icons/icon_02_photos.svg'
import albums from '../../assets/xuanbox-icons/icon_03_albums.svg'
import files from '../../assets/xuanbox-icons/icon_04_files.svg'
import receipts from '../../assets/xuanbox-icons/icon_06_receipts.svg'
import documents from '../../assets/xuanbox-icons/icon_07_documents.svg'
import search from '../../assets/xuanbox-icons/icon_09_search.svg'
import share from '../../assets/xuanbox-icons/icon_12_share.svg'
import xuandrop from '../../assets/xuanbox-icons/icon_13_xuandrop.svg'
import upload from '../../assets/xuanbox-icons/icon_14_upload.svg'
import download from '../../assets/xuanbox-icons/icon_15_download.svg'
import trash from '../../assets/xuanbox-icons/icon_16_trash.svg'
import settings from '../../assets/xuanbox-icons/icon_21_settings.svg'
import users from '../../assets/xuanbox-icons/icon_22_users.svg'
import admin from '../../assets/xuanbox-icons/icon_23_admin.svg'
import storage from '../../assets/xuanbox-icons/icon_27_storage.svg'
import notifications from '../../assets/xuanbox-icons/icon_28_notifications.svg'
import logo from '../../assets/xuanbox-icons/logo_app_icon.svg'
import logoHorizontal from '../../assets/xuanbox-icons/logo_horizontal_lockup.svg'

const icons = {
  dashboard,
  photos,
  albums,
  files,
  receipts,
  documents,
  search,
  share,
  xuandrop,
  upload,
  download,
  trash,
  settings,
  users,
  admin,
  storage,
  notifications,
  logo,
  logoHorizontal
}

const props = defineProps({
  name: {
    type: String,
    required: true
  },
  size: {
    type: [Number, String],
    default: 20
  },
  label: {
    type: String,
    default: ''
  }
})
</script>

<template>
  <img
    class="xb-asset-icon"
    :src="icons[props.name]"
    :alt="props.label"
    :aria-hidden="props.label ? 'false' : 'true'"
    :style="{ width: `${props.size}px`, height: `${props.size}px` }"
  />
</template>
