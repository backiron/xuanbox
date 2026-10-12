const DEVICE_KEY_STORAGE = 'xb_device_key'

function randomKey() {
  const bytes = new Uint8Array(24)
  window.crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

// A random key kept in this browser so signing in again reuses the same XuanDrop device.
export function getDeviceKey() {
  try {
    let key = localStorage.getItem(DEVICE_KEY_STORAGE)
    if (!key) {
      key = randomKey()
      localStorage.setItem(DEVICE_KEY_STORAGE, key)
    }
    return key
  } catch {
    return undefined
  }
}

export function defaultDeviceName() {
  const ua = navigator.userAgent || ''
  const isIpadOs = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1
  let device = 'Browser'
  if (/iPhone/.test(ua)) device = 'iPhone'
  else if (/iPad/.test(ua) || isIpadOs) device = 'iPad'
  else if (/Android/.test(ua)) device = /Mobile/.test(ua) ? 'Android' : 'Android Tablet'
  else if (/Windows/.test(ua)) device = 'Windows'
  else if (/Macintosh/.test(ua)) device = 'Mac'
  else if (/Linux/.test(ua)) device = 'Linux'

  let browser = ''
  if (/EdgA?\//.test(ua)) browser = 'Edge'
  else if (/SamsungBrowser\//.test(ua)) browser = 'Samsung Internet'
  else if (/(Chrome|CriOS)\//.test(ua)) browser = 'Chrome'
  else if (/(Firefox|FxiOS)\//.test(ua)) browser = 'Firefox'
  else if (/Safari\//.test(ua)) browser = 'Safari'
  return browser ? `${device} · ${browser}` : device
}

export function deviceFields() {
  return { device_name: defaultDeviceName(), device_key: getDeviceKey() }
}
