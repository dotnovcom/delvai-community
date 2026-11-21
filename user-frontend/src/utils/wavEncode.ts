function writeString(view: DataView, offset: number, text: string) {
  for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i))
}

function audioBufferToWav(buffer: AudioBuffer) {
  const length = buffer.length
  const left = buffer.getChannelData(0)
  const right = buffer.numberOfChannels > 1 ? buffer.getChannelData(1) : null
  const samples = new Int16Array(length)
  for (let i = 0; i < length; i += 1) {
    const sample = right ? (left[i] + right[i]) / 2 : left[i]
    const clamped = Math.max(-1, Math.min(1, sample))
    samples[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
  }
  const dataSize = samples.length * 2
  const out = new ArrayBuffer(44 + dataSize)
  const view = new DataView(out)
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, buffer.sampleRate, true)
  view.setUint32(28, buffer.sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)
  new Int16Array(out, 44).set(samples)
  return out
}

/** 浏览器录音多为 webm，MiMo 只收 wav / mp3。 */
export async function blobToWav(blob: Blob) {
  const ctx = new AudioContext()
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer())
    return new Blob([audioBufferToWav(decoded)], { type: 'audio/wav' })
  } finally {
    await ctx.close().catch(() => {})
  }
}
