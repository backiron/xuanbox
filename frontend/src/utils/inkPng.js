// A handwriting page is saved as an ordinary PNG with its strokes in a private chunk, so the note
// shows a plain image everywhere while the board can open it again for more writing.
const CHUNK = 'xbIk' // ancillary, private, safe to copy
const SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10]

let crcTable = null
function crc32(bytes) {
  if (!crcTable) {
    crcTable = new Uint32Array(256)
    for (let n = 0; n < 256; n++) {
      let c = n
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
      crcTable[n] = c >>> 0
    }
  }
  let crc = 0xffffffff
  for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

function isPng(bytes) {
  return bytes.length > 8 && SIGNATURE.every((value, i) => bytes[i] === value)
}

/** Insert the strokes as a chunk right before IEND. */
export async function embedInk(pngBlob, ink) {
  const bytes = new Uint8Array(await pngBlob.arrayBuffer())
  const data = new TextEncoder().encode(JSON.stringify(ink))
  const chunk = new Uint8Array(12 + data.length)
  const view = new DataView(chunk.buffer)
  view.setUint32(0, data.length)
  chunk.set(new TextEncoder().encode(CHUNK), 4)
  chunk.set(data, 8)
  view.setUint32(8 + data.length, crc32(chunk.subarray(4, 8 + data.length)))
  const iend = bytes.length - 12
  return new Blob([bytes.subarray(0, iend), chunk, bytes.subarray(iend)], { type: 'image/png' })
}

/** The strokes saved in a handwriting PNG, or null for any other image. */
export async function readInk(blob) {
  if (!blob || blob.type !== 'image/png') return null
  const bytes = new Uint8Array(await blob.arrayBuffer())
  if (!isPng(bytes)) return null
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  let offset = 8
  while (offset + 12 <= bytes.length) {
    const length = view.getUint32(offset)
    const type = String.fromCharCode(...bytes.subarray(offset + 4, offset + 8))
    if (type === CHUNK) {
      try {
        const ink = JSON.parse(new TextDecoder().decode(bytes.subarray(offset + 8, offset + 8 + length)))
        return ink?.v === 1 && Array.isArray(ink.strokes) ? ink : null
      } catch {
        return null
      }
    }
    if (type === 'IEND') return null
    offset += 12 + length
  }
  return null
}
