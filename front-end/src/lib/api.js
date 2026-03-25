const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

async function readJsonOrThrow(res, fallbackMessage) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || fallbackMessage || res.statusText)
  }
  return res.json()
}

export async function sendChat({ sessionId, message, quickReplyId }) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId || null,
      message: message || '',
      quick_reply_id: quickReplyId || null,
    }),
  })
  return readJsonOrThrow(res, 'Chat request failed')
}

export async function transcribeVoice(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/voice-to-text`, { method: 'POST', body: fd })
  return readJsonOrThrow(res, 'Transcription failed')
}

/** Recorded in-browser audio (e.g. MediaRecorder webm). Malayalam etc. → English on server when Gemini is configured. */
export async function transcribeVoiceBlob(blob, filename = 'recording.webm') {
  const file = new File([blob], filename, { type: blob.type || 'audio/webm' })
  return transcribeVoice(file)
}

export async function fetchDashboard() {
  const [d, m, history] = await Promise.all([
    fetch(`${API_BASE}/dashboard-data`).then((r) => readJsonOrThrow(r, 'Dashboard request failed')),
    fetch(`${API_BASE}/map-data`).then((r) => readJsonOrThrow(r, 'Map request failed')),
    fetch(`${API_BASE}/history`).then((r) => readJsonOrThrow(r, 'History request failed')),
  ])
  return { dashboard: d, mapPoints: m, history }
}

export { API_BASE }
