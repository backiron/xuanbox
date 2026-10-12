import { onBeforeUnmount, ref } from 'vue'
import { dropChatApi } from '../api/dropChatApi'

// One WebSocket per open XuanDrop page. Reconnects with backoff, and immediately when the tab
// becomes visible again (mobile browsers drop sockets in the background).
export function useDropSocket(onEvent) {
  const status = ref('offline')
  let socket = null
  let pingTimer = null
  let retryTimer = null
  let retryDelay = 1000
  let stopped = false
  let lastFrameAt = 0

  function socketUrl(ticket) {
    const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const url = new URL(`${base}/drop/ws`, window.location.href)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.searchParams.set('ticket', ticket)
    return url.toString()
  }

  function clearTimers() {
    window.clearInterval(pingTimer)
    window.clearTimeout(retryTimer)
    pingTimer = null
    retryTimer = null
  }

  function scheduleReconnect() {
    if (stopped) return
    status.value = 'reconnecting'
    window.clearTimeout(retryTimer)
    retryTimer = window.setTimeout(connect, retryDelay)
    retryDelay = Math.min(retryDelay * 2, 15000)
  }

  async function connect() {
    if (stopped) return
    clearTimers()
    if (socket && socket.readyState <= WebSocket.OPEN) return
    status.value = status.value === 'online' ? 'reconnecting' : 'connecting'
    let ticket
    let pingSeconds = 20
    try {
      const response = await dropChatApi.wsTicket()
      ticket = response.data.data.ticket
      pingSeconds = response.data.data.ping_interval_seconds || pingSeconds
    } catch {
      scheduleReconnect()
      return
    }
    if (stopped) return
    const current = new WebSocket(socketUrl(ticket))
    socket = current
    current.onopen = () => {
      status.value = 'online'
      retryDelay = 1000
      lastFrameAt = Date.now()
      pingTimer = window.setInterval(() => {
        if (current.readyState !== WebSocket.OPEN) return
        // No pong for two intervals: the connection is silently dead (common after a phone sleeps).
        if (Date.now() - lastFrameAt > pingSeconds * 2500) {
          current.close()
          return
        }
        current.send('ping')
      }, pingSeconds * 1000)
      onEvent({ event: 'socket.open' })
    }
    current.onmessage = (event) => {
      lastFrameAt = Date.now()
      try {
        const message = JSON.parse(event.data)
        if (message.event !== 'pong') onEvent(message)
      } catch {
        // ignore malformed frames
      }
    }
    current.onclose = () => {
      if (socket === current) socket = null
      window.clearInterval(pingTimer)
      scheduleReconnect()
    }
    current.onerror = () => current.close()
  }

  function onVisibility() {
    if (document.visibilityState !== 'visible' || stopped) return
    if (!socket || socket.readyState > WebSocket.OPEN) {
      retryDelay = 1000
      connect()
    } else if (socket.readyState === WebSocket.OPEN) {
      const current = socket
      const sentAt = Date.now()
      current.send('ping')
      window.setTimeout(() => {
        if (socket === current && lastFrameAt < sentAt) current.close()
      }, 4000)
    }
  }

  function start() {
    stopped = false
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('online', onVisibility)
    connect()
  }

  function stop() {
    stopped = true
    clearTimers()
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('online', onVisibility)
    if (socket) socket.close()
    socket = null
    status.value = 'offline'
  }

  onBeforeUnmount(stop)
  return { status, start, stop }
}
