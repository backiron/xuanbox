<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Eraser, Hand, PenLine, Redo2, Trash2, Undo2, X } from 'lucide-vue-next'
import { useDialogStore } from '../../stores/dialogStore'
import { embedInk } from '../../utils/inkPng'

/**
 * Full-screen handwriting page.
 *
 * Works with Apple Pencil (Safari), Samsung S Pen and USI pens on Chromebooks / Pixel tablets
 * (Chrome, Samsung Internet), Wacom/Surface pens, fingers and mice through Pointer Events:
 * - pressure changes the line width for pens;
 * - once a pen has touched the page, fingers and palms no longer draw (the hand button turns finger
 *   drawing back on);
 * - the pen's eraser end (Surface, Wacom) and the S Pen / barrel side button erase while held.
 * Strokes are kept as vectors in page units, so rotating the device or resizing the window only
 * re-fits the page; nothing is lost or blurred.
 */
const props = defineProps({
  ink: { type: Object, default: null } // existing page to keep writing on
})
const emit = defineEmits(['close', 'save'])

const { t } = useI18n()
const dialog = useDialogStore()

const COLORS = ['#111827', '#2563eb', '#dc2626', '#16a34a', '#d97706']
const SIZES = [2, 4, 8]
const EXPORT_SIDE = 2400 // stays under the server's 2560 px limit so the PNG (and its strokes) is kept as is
const PEN_SEEN_KEY = 'xb_ink_pen_seen'

const stageRef = ref(null)
const canvasRef = ref(null)
const tool = ref('pen')
const color = ref(COLORS[0])
const size = ref(SIZES[1])
const fingerDraws = ref(true)
const saving = ref(false)
// Plain arrays (not reactive): thousands of points per page, and undo compares strokes by identity.
let strokes = []
let undoStack = []
let redoStack = []
const counts = ref({ strokes: 0, undo: 0, redo: 0 })
const view = ref({ scale: 1, width: 0, height: 0 })

// Page size in page units: portrait on tall screens, landscape on wide ones, fixed once created.
const page = ref(props.ink ? { w: props.ink.w, h: props.ink.h } : null)
const dirty = computed(() => counts.value.undo > 0)

function sync() {
  counts.value = { strokes: strokes.length, undo: undoStack.length, redo: redoStack.length }
}

let ctx = null
let active = null // { pointerId, pointerType, erasing, stroke }
let resizeObserver = null

function readPenSeen() {
  try {
    return localStorage.getItem(PEN_SEEN_KEY) === '1'
  } catch {
    return false
  }
}

function rememberPen() {
  try {
    localStorage.setItem(PEN_SEEN_KEY, '1')
  } catch {
    // private mode: palm rejection still applies for this session
  }
}

// ---------------------------------------------------------------- layout

function fit() {
  const stage = stageRef.value
  const canvas = canvasRef.value
  if (!stage || !canvas) return
  const style = getComputedStyle(stage)
  const availW = stage.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
  const availH = stage.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)
  if (!availW || !availH) return
  if (!page.value) page.value = availW > availH ? { w: 1400, h: 1000 } : { w: 1000, h: 1400 }
  const scale = Math.min(availW / page.value.w, availH / page.value.h)
  const width = Math.floor(page.value.w * scale)
  const height = Math.floor(page.value.h * scale)
  // Sharp on high-density screens without exceeding mobile canvas memory limits.
  const dpr = Math.min(window.devicePixelRatio || 1, 3, Math.sqrt(16_000_000 / (width * height)))
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
  canvas.width = Math.round(width * dpr)
  canvas.height = Math.round(height * dpr)
  ctx = canvas.getContext('2d')
  ctx.setTransform(scale * dpr, 0, 0, scale * dpr, 0, 0)
  view.value = { scale, width, height }
  redraw()
}

// ---------------------------------------------------------------- drawing

function widthAt(stroke, i) {
  const pressure = stroke.p[i * 3 + 2]
  return stroke.s * (stroke.pen ? 0.35 + (pressure / 100) * 1.3 : 1)
}

function point(stroke, i) {
  return { x: stroke.p[i * 3], y: stroke.p[i * 3 + 1] }
}

// Segment i of a stroke: a quadratic curve through the midpoints, so lines stay smooth.
function drawSegment(target, stroke, i) {
  const count = stroke.p.length / 3
  target.strokeStyle = stroke.c
  target.fillStyle = stroke.c
  target.lineCap = 'round'
  target.lineJoin = 'round'
  if (count === 1) {
    const p = point(stroke, 0)
    target.beginPath()
    target.arc(p.x, p.y, widthAt(stroke, 0) / 2, 0, Math.PI * 2)
    target.fill()
    return
  }
  const p0 = point(stroke, Math.max(i - 2, 0))
  const p1 = point(stroke, i - 1)
  const p2 = point(stroke, i)
  const start = i === 1 ? p0 : { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 }
  const end = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 }
  target.lineWidth = widthAt(stroke, i - 1)
  target.beginPath()
  target.moveTo(start.x, start.y)
  target.quadraticCurveTo(p1.x, p1.y, end.x, end.y)
  if (i === count - 1) target.lineTo(p2.x, p2.y)
  target.stroke()
}

function drawStroke(target, stroke) {
  const count = stroke.p.length / 3
  if (count === 1) drawSegment(target, stroke, 0)
  for (let i = 1; i < count; i++) drawSegment(target, stroke, i)
}

function paintPage(target) {
  target.fillStyle = '#ffffff'
  target.fillRect(0, 0, page.value.w, page.value.h)
  strokes.forEach((stroke) => drawStroke(target, stroke))
}

function redraw() {
  if (!ctx || !page.value) return
  paintPage(ctx)
}

function pagePoint(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  const { scale } = view.value
  const x = Math.min(Math.max((event.clientX - rect.left) / scale, 0), page.value.w)
  const y = Math.min(Math.max((event.clientY - rect.top) / scale, 0), page.value.h)
  // Mice report 0.5 while pressed; some pens report 0 on the first sample.
  const pressure = event.pointerType === 'pen' ? (event.pressure || 0.5) : 0.5
  return [Math.round(x * 10) / 10, Math.round(y * 10) / 10, Math.round(pressure * 100)]
}

function isEraserInput(event) {
  // buttons 32 = eraser end (Surface, Wacom); 2 = barrel / S Pen side button held.
  return tool.value === 'eraser' || (event.pointerType === 'pen' && (event.buttons & 32 || event.buttons & 2))
}

function eraseAt([x, y]) {
  const radius = Math.max(10, size.value * 2.5)
  const removed = []
  strokes = strokes.filter((stroke, index) => {
    for (let i = 0; i < stroke.p.length; i += 3) {
      const dx = stroke.p[i] - x
      const dy = stroke.p[i + 1] - y
      const reach = radius + stroke.s
      if (dx * dx + dy * dy <= reach * reach) {
        removed.push({ index, stroke })
        return false
      }
    }
    return true
  })
  if (removed.length) {
    active.erased.push(...removed)
    sync()
    redraw()
  }
}

function onPointerDown(event) {
  if (event.pointerType === 'pen') {
    if (fingerDraws.value && !readPenSeen()) fingerDraws.value = false
    rememberPen()
    // A palm that landed first must not leave a mark once the pen arrives.
    if (active && active.pointerType === 'touch') cancelActive()
  }
  if (active) return
  if (event.pointerType === 'touch' && !fingerDraws.value) return
  if (event.pointerType === 'mouse' && event.button !== 0) return
  event.preventDefault()
  try {
    canvasRef.value.setPointerCapture(event.pointerId)
  } catch {
    // capture is best effort; strokes still end on pointerup
  }
  const erasing = isEraserInput(event)
  active = { pointerId: event.pointerId, pointerType: event.pointerType, erasing, erased: [], stroke: null }
  if (erasing) {
    eraseAt(pagePoint(event))
    return
  }
  const stroke = { c: color.value, s: size.value, pen: event.pointerType === 'pen', p: pagePoint(event) }
  active.stroke = stroke
  strokes.push(stroke)
  sync()
  drawSegment(ctx, stroke, 0)
}

function onPointerMove(event) {
  if (!active || event.pointerId !== active.pointerId) return
  event.preventDefault()
  const samples = event.getCoalescedEvents?.() || []
  for (const sample of samples.length ? samples : [event]) {
    const next = pagePoint(sample)
    if (active.erasing) {
      eraseAt(next)
      continue
    }
    const stroke = active.stroke
    const n = stroke.p.length
    // Skip samples closer than a quarter of a page unit: no visible change, much smaller files.
    if (Math.abs(stroke.p[n - 3] - next[0]) < 0.25 && Math.abs(stroke.p[n - 2] - next[1]) < 0.25) continue
    stroke.p.push(...next)
    drawSegment(ctx, stroke, stroke.p.length / 3 - 1)
  }
}

function onPointerUp(event) {
  if (!active || event.pointerId !== active.pointerId) return
  if (active.erasing) {
    if (active.erased.length) pushHistory({ type: 'erase', items: active.erased })
  } else {
    pushHistory({ type: 'add', stroke: active.stroke })
  }
  active = null
  sync()
}

function cancelActive() {
  if (active?.stroke) strokes = strokes.filter((stroke) => stroke !== active.stroke)
  if (active?.erased.length) restoreErased(active.erased)
  active = null
  sync()
  redraw()
}

// ---------------------------------------------------------------- history

function pushHistory(entry) {
  undoStack.push(entry)
  redoStack = []
  sync()
}

function restoreErased(items) {
  const list = [...strokes]
  ;[...items].sort((a, b) => a.index - b.index).forEach(({ index, stroke }) => list.splice(index, 0, stroke))
  strokes = list
}

function undo() {
  const entry = undoStack.pop()
  if (!entry) return
  if (entry.type === 'add') strokes = strokes.filter((stroke) => stroke !== entry.stroke)
  if (entry.type === 'erase') restoreErased(entry.items)
  if (entry.type === 'clear') strokes = entry.strokes
  redoStack.push(entry)
  sync()
  redraw()
}

function redo() {
  const entry = redoStack.pop()
  if (!entry) return
  if (entry.type === 'add') strokes.push(entry.stroke)
  if (entry.type === 'erase') {
    const gone = new Set(entry.items.map((item) => item.stroke))
    strokes = strokes.filter((stroke) => !gone.has(stroke))
  }
  if (entry.type === 'clear') strokes = []
  undoStack.push(entry)
  sync()
  redraw()
}

function clearPage() {
  if (!strokes.length) return
  pushHistory({ type: 'clear', strokes: strokes })
  strokes = []
  sync()
  redraw()
}

// ---------------------------------------------------------------- save / close

async function save() {
  if (saving.value) return
  if (!dirty.value) {
    emit('close')
    return
  }
  saving.value = true
  try {
    const scale = EXPORT_SIDE / Math.max(page.value.w, page.value.h)
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(page.value.w * scale)
    canvas.height = Math.round(page.value.h * scale)
    const target = canvas.getContext('2d')
    target.setTransform(scale, 0, 0, scale, 0, 0)
    paintPage(target)
    const png = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    const ink = { v: 1, w: page.value.w, h: page.value.h, strokes: strokes }
    const blob = await embedInk(png, ink)
    emit('save', new File([blob], `handwriting-${Date.now()}.png`, { type: 'image/png' }))
  } finally {
    saving.value = false
  }
}

async function close() {
  if (dirty.value) {
    const leave = await dialog.confirm({
      title: t('pages.notes.ink.discardTitle'),
      message: t('pages.notes.ink.discardMessage'),
      confirmText: t('pages.notes.ink.discard'),
      cancelText: t('common.actions.cancel')
    })
    if (!leave) return
  }
  emit('close')
}

function onKeydown(event) {
  const mod = event.ctrlKey || event.metaKey
  if (mod && event.key.toLowerCase() === 'z') {
    event.preventDefault()
    if (event.shiftKey) redo()
    else undo()
  } else if (mod && event.key.toLowerCase() === 'y') {
    event.preventDefault()
    redo()
  } else if (event.key === 'Escape') {
    close()
  }
}

// iOS Safari shows a magnifier / selection on long presses unless touches on the page are cancelled.
function blockTouch(event) {
  event.preventDefault()
}

onMounted(async () => {
  fingerDraws.value = !readPenSeen()
  if (props.ink) strokes = props.ink.strokes.map((stroke) => ({ ...stroke, p: [...stroke.p] }))
  sync()
  document.documentElement.classList.add('xb-ink-open')
  window.addEventListener('keydown', onKeydown)
  await nextTick()
  canvasRef.value.addEventListener('touchstart', blockTouch, { passive: false })
  canvasRef.value.addEventListener('touchmove', blockTouch, { passive: false })
  resizeObserver = new ResizeObserver(() => fit())
  resizeObserver.observe(stageRef.value)
  fit()
})

onBeforeUnmount(() => {
  document.documentElement.classList.remove('xb-ink-open')
  window.removeEventListener('keydown', onKeydown)
  canvasRef.value?.removeEventListener('touchstart', blockTouch)
  canvasRef.value?.removeEventListener('touchmove', blockTouch)
  resizeObserver?.disconnect()
})
</script>

<template>
  <Teleport to="body">
    <div class="xb-ink" role="dialog" aria-modal="true" :aria-label="t('pages.notes.ink.title')">
      <header class="xb-ink-bar">
        <button class="xb-ink-btn" type="button" :title="t('common.actions.cancel')" @click="close">
          <X :size="20" />
        </button>
        <div class="xb-ink-tools">
          <button class="xb-ink-btn" :class="{ 'is-active': tool === 'pen' }" type="button" :title="t('pages.notes.ink.pen')" @click="tool = 'pen'">
            <PenLine :size="20" />
          </button>
          <button class="xb-ink-btn" :class="{ 'is-active': tool === 'eraser' }" type="button" :title="t('pages.notes.ink.eraser')" @click="tool = 'eraser'">
            <Eraser :size="20" />
          </button>
          <span class="xb-ink-sep"></span>
          <button
            v-for="item in COLORS"
            :key="item"
            class="xb-ink-color"
            :class="{ 'is-active': color === item && tool === 'pen' }"
            type="button"
            :style="{ '--ink': item }"
            :title="t('pages.notes.ink.color')"
            @click="color = item; tool = 'pen'"
          ></button>
          <span class="xb-ink-sep"></span>
          <button
            v-for="item in SIZES"
            :key="item"
            class="xb-ink-btn xb-ink-size"
            :class="{ 'is-active': size === item }"
            type="button"
            :title="t('pages.notes.ink.size')"
            @click="size = item"
          >
            <span :style="{ width: `${item + 3}px`, height: `${item + 3}px` }"></span>
          </button>
          <span class="xb-ink-sep"></span>
          <button class="xb-ink-btn" type="button" :disabled="!counts.undo" :title="t('pages.notes.ink.undo')" @click="undo">
            <Undo2 :size="20" />
          </button>
          <button class="xb-ink-btn" type="button" :disabled="!counts.redo" :title="t('pages.notes.ink.redo')" @click="redo">
            <Redo2 :size="20" />
          </button>
          <button class="xb-ink-btn" type="button" :disabled="!counts.strokes" :title="t('pages.notes.ink.clear')" @click="clearPage">
            <Trash2 :size="20" />
          </button>
          <button
            class="xb-ink-btn"
            :class="{ 'is-active': fingerDraws }"
            type="button"
            :title="fingerDraws ? t('pages.notes.ink.fingerOn') : t('pages.notes.ink.fingerOff')"
            :aria-pressed="fingerDraws"
            @click="fingerDraws = !fingerDraws"
          >
            <Hand :size="20" />
          </button>
        </div>
        <button class="xb-ink-btn xb-ink-done" type="button" :disabled="saving" @click="save">
          <Check :size="20" />
          <span>{{ t('pages.notes.ink.done') }}</span>
        </button>
      </header>
      <div ref="stageRef" class="xb-ink-stage">
        <canvas
          ref="canvasRef"
          class="xb-ink-canvas"
          :class="{ 'is-erasing': tool === 'eraser' }"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
          @pointercancel="onPointerUp"
          @lostpointercapture="onPointerUp"
          @contextmenu.prevent
        ></canvas>
      </div>
    </div>
  </Teleport>
</template>
