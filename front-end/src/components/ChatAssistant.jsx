import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LoaderCircle, Mic, Send, Sparkles, Square } from 'lucide-react'
import { sendChat, transcribeVoice, transcribeVoiceBlob } from '../lib/api'
import { RichText } from './RichText'

export function ChatAssistant() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [recording, setRecording] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState(null)
  const bottomRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const speechRecRef = useRef(null)

  const pushAssistant = useCallback((payload) => {
    setMessages((m) => [
      ...m,
      {
        role: 'assistant',
        text: payload.assistant_message,
        quickReplies: payload.quick_replies || [],
        card: payload.summary_card,
        scam: payload.scam_banner,
        caseComplete: payload.case_complete,
        stage: payload.stage,
        chatMode: payload.chat_mode || 'free',
        chatSignals: payload.chat_signals || null,
        intentStatus: payload.chat_mode === 'civic' ? payload.frontend_status || null : null,
        intentAnalysis: payload.chat_mode === 'civic' ? payload.intent_analysis || null : null,
      },
    ])
  }, [])

  const bootstrap = useCallback(async () => {
    setLoading(true)
    try {
      const data = await sendChat({ sessionId: null, message: '', quickReplyId: null })
      setSessionId(data.session_id)
      pushAssistant(data)
    } catch (e) {
      setMessages([{ role: 'assistant', text: `Could not reach CivicSafe backend: ${e.message}`, quickReplies: [] }])
    } finally {
      setLoading(false)
    }
  }, [pushAssistant])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    if (speechRecRef.current) {
      try {
        speechRecRef.current.stop()
      } catch {}
    }
  }, [])

  const runTurn = async ({ message, quickReplyId }) => {
    setLoading(true)
    try {
      const data = await sendChat({ sessionId, message: message || '', quickReplyId: quickReplyId || null })
      setSessionId(data.session_id)
      if (message?.trim()) {
        setMessages((m) => [...m, { role: 'user', text: message }])
      }
      pushAssistant(data)
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: `Something went wrong: ${e.message}`, quickReplies: [] }])
    } finally {
      setLoading(false)
      setInput('')
    }
  }

  const handleTranscriptionResult = (result) => {
    const text = (result?.converted_text || '').trim()
    if (text) {
      setInput((prev) => (prev ? `${prev} ${text}` : text).trim())
    }
    const lang = (result?.detected_language || result?.language || '').trim()
    const langNote =
      result?.mode === 'live' && lang
        ? ` Detected speech language (Whisper): ${lang}.`
        : ''
    setVoiceStatus({
      tone: result?.mode === 'live' ? 'ok' : 'warn',
      text:
        result?.mode === 'live'
          ? `Voice transcribed with Whisper (multilingual).${langNote} Edit below before sending.`
          : result?.detail || 'Voice could not be transcribed. Set OPENAI_API_KEY and restart the API.',
    })
  }

  const onSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    runTurn({ message: input })
  }

  const startRecording = async () => {
    if (recording || voiceBusy) return
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      try {
        const rec = new SpeechRecognition()
        speechRecRef.current = rec
        rec.lang = 'en-IN'
        rec.continuous = false
        rec.interimResults = false
        rec.onresult = (event) => {
          const transcript = event?.results?.[0]?.[0]?.transcript?.trim()
          if (transcript) {
            setInput((prev) => (prev ? `${prev} ${transcript}` : transcript).trim())
            setVoiceStatus({
              tone: 'ok',
              text: 'Voice transcribed using browser speech recognition. Edit text before sending.',
            })
          }
        }
        rec.onerror = () => {
          setVoiceStatus({
            tone: 'warn',
            text: 'Browser speech recognition failed; trying server transcription fallback.',
          })
        }
        rec.onend = () => {
          setRecording(false)
          speechRecRef.current = null
        }
        setVoiceStatus(null)
        rec.start()
        setRecording(true)
        return
      } catch {
        // Fall through to MediaRecorder + backend.
      }
    }
    try {
      setVoiceStatus(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime })
      mediaRecorderRef.current = recorder
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        const blob = new Blob(chunksRef.current, { type: mime })
        chunksRef.current = []
        if (!blob.size) {
          setVoiceBusy(false)
          return
        }
        setVoiceBusy(true)
        try {
          const result = await transcribeVoiceBlob(blob, 'voice.webm')
          handleTranscriptionResult(result)
        } catch (error) {
          setVoiceStatus({ tone: 'error', text: error.message || 'Voice transcription failed.' })
        } finally {
          setVoiceBusy(false)
        }
      }
      recorder.start(300)
      setRecording(true)
    } catch {
      setRecording(false)
      setVoiceStatus({ tone: 'error', text: 'Microphone access was not available.' })
    }
  }

  const stopRecording = () => {
    const speech = speechRecRef.current
    if (speech) {
      try {
        speech.stop()
      } catch {}
      speechRecRef.current = null
      setRecording(false)
      return
    }
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
    mediaRecorderRef.current = null
    setRecording(false)
  }

  const onVoiceFile = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setVoiceBusy(true)
    setVoiceStatus(null)
    try {
      const result = await transcribeVoice(file)
      handleTranscriptionResult(result)
    } catch (error) {
      setInput('')
      setVoiceStatus({ tone: 'error', text: error.message || 'Voice transcription failed.' })
    } finally {
      setVoiceBusy(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="glass-panel mb-4 flex shrink-0 flex-col gap-3 rounded-2xl border border-white/[0.07] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-emerald-300/90">Assistant</p>
          <h2 className="text-lg font-semibold text-white">Complaints, requests, and voice in many languages</h2>
          <p className="text-sm text-slate-400">
            Outages and faults are logged as complaints; new connections and applications as requests. Mic uses OpenAI Whisper—set{' '}
            <span className="font-mono text-[11px] text-slate-500">TRANSCRIBE_TRANSLATE=1</span> in the backend to normalize to English.
          </p>
          {voiceStatus ? (
            <p className={`mt-2 text-xs ${voiceStatus.tone === 'ok' ? 'text-emerald-300' : voiceStatus.tone === 'error' ? 'text-rose-300' : 'text-amber-300'}`}>
              {voiceStatus.text}
            </p>
          ) : null}
        </div>
        <Sparkles className="h-8 w-8 text-cyan-400/80" />
      </div>

      <div className="glass-panel flex min-h-[420px] flex-1 flex-col overflow-hidden rounded-2xl sm:min-h-[560px]">
        <div className="custom-scrollbar flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          <AnimatePresence initial={false}>
            {messages.map((msg, idx) => (
              <motion.div key={idx} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[min(100%,42rem)] rounded-2xl px-4 py-3 text-sm ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-cyan-600/90 to-indigo-600/90 text-white shadow-glow'
                      : 'border border-white/10 bg-white/5 text-slate-100'
                  }`}
                >
                  {msg.role === 'user' ? msg.text : <RichText text={msg.text} />}
                  {msg.chatMode === 'civic' && msg.intentStatus && msg.role === 'assistant' ? (
                    <div className="mt-4 rounded-xl border border-cyan-500/25 bg-gradient-to-br from-cyan-950/40 to-indigo-950/30 p-4 text-left">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-cyan-300/90">Case status</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[11px] font-medium text-slate-200">
                          {msg.intentStatus.chat_type || 'Intent'}
                        </span>
                        {msg.intentStatus.priority_badge && msg.intentStatus.priority_badge !== '—' ? (
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                              String(msg.intentStatus.priority_badge).toLowerCase() === 'high'
                                ? 'bg-rose-500/20 text-rose-200 ring-1 ring-rose-500/30'
                                : 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/25'
                            }`}
                          >
                            Priority: {msg.intentStatus.priority_badge}
                          </span>
                        ) : null}
                        {msg.intentStatus.escalation_status === 'Escalated' ? (
                          <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[11px] font-medium text-amber-100 ring-1 ring-amber-400/30">
                            Escalated
                          </span>
                        ) : null}
                      </div>
                      {msg.intentStatus.title ? (
                        <p className="mt-2 text-sm font-semibold text-white">{msg.intentStatus.title}</p>
                      ) : null}
                      {msg.intentStatus.subtitle ? (
                        <p className="text-xs text-slate-400">{msg.intentStatus.subtitle}</p>
                      ) : null}
                      {msg.intentStatus.group_warning ? (
                        <p className="mt-2 rounded-lg border border-amber-500/30 bg-amber-950/40 px-3 py-2 text-xs text-amber-100">
                          {msg.intentStatus.group_warning}
                        </p>
                      ) : null}
                      <dl className="mt-3 grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
                        {msg.intentStatus.allocation_status ? (
                          <div className="flex justify-between gap-2 border-b border-white/5 pb-1">
                            <dt className="text-slate-500">Allocation</dt>
                            <dd className="text-right text-slate-200">{msg.intentStatus.allocation_status}</dd>
                          </div>
                        ) : null}
                        {msg.intentStatus.authority_status ? (
                          <div className="flex justify-between gap-2 border-b border-white/5 pb-1">
                            <dt className="text-slate-500">Authority</dt>
                            <dd className="text-right text-slate-200">{msg.intentStatus.authority_status}</dd>
                          </div>
                        ) : null}
                      </dl>
                      {Array.isArray(msg.intentStatus.timeline) && msg.intentStatus.timeline.length > 0 ? (
                        <ol className="mt-3 space-y-1.5 border-t border-white/10 pt-3 text-[11px] text-slate-400">
                          {msg.intentStatus.timeline.map((step, si) => (
                            <li key={si} className="flex gap-2">
                              <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full bg-cyan-500/20 text-center text-[10px] leading-4 text-cyan-200">
                                {si + 1}
                              </span>
                              <span className="text-slate-300">{step}</span>
                            </li>
                          ))}
                        </ol>
                      ) : null}
                    </div>
                  ) : null}
                  {msg.scam?.show ? (
                    <div className="mt-3 rounded-xl border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-100">
                      <p className="font-semibold text-rose-200">{msg.scam.headline}</p>
                      <p className="mt-1 text-rose-100/90">{msg.scam.advice}</p>
                      <p className="mt-2 text-rose-200/80">{msg.scam.escalation}</p>
                    </div>
                  ) : null}
                  {msg.card ? (
                    <div className="mt-4 rounded-xl border border-white/10 bg-black/30 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300/90">Summary</p>
                      <p className="mt-1 text-base font-semibold text-white">{msg.card.title}</p>
                      {msg.card.subtitle ? <p className="text-sm text-slate-400">{msg.card.subtitle}</p> : null}
                      <dl className="mt-3 space-y-2 text-sm">
                        {(msg.card.fields || []).map((field, index) => (
                          <div key={index} className="flex justify-between gap-4 border-b border-white/5 py-1">
                            <dt className="text-slate-500">{field.label}</dt>
                            <dd className="text-right text-slate-200">{field.value}</dd>
                          </div>
                        ))}
                      </dl>
                      {(msg.card.badges || []).length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {msg.card.badges.map((badge) => (
                            <span key={badge} className="rounded-full bg-cyan-500/20 px-2 py-0.5 text-xs text-cyan-200">
                              {badge}
                            </span>
                          ))}
                        </div>
                      ) : null}
                      {(msg.card.next_steps || []).length > 0 ? (
                        <ol className="mt-3 list-decimal space-y-1 pl-4 text-xs text-slate-300">
                          {msg.card.next_steps.map((step, index) => (
                            <li key={index}>{step}</li>
                          ))}
                        </ol>
                      ) : null}
                    </div>
                  ) : null}
                  {msg.quickReplies?.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {msg.quickReplies.map((reply) => (
                        <button
                          key={reply.id}
                          type="button"
                          disabled={loading}
                          onClick={() => runTurn({ message: '', quickReplyId: reply.id })}
                          className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-medium text-cyan-100 transition hover:border-cyan-400/50 hover:bg-cyan-500/10 disabled:opacity-50"
                        >
                          {reply.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {loading ? (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-400">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Thinking...
              </div>
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={onSubmit} className="border-t border-white/10 p-3 sm:p-4">
          {recording ? (
            <p className="mb-2 flex items-center gap-2 text-xs font-medium text-rose-300">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-rose-500" />
              Recording... tap stop to transcribe.
            </p>
          ) : null}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={2}
              placeholder="Describe a problem, a new connection, or use the mic (Malayalam, Hindi, English, …)"
              className="min-h-[3rem] flex-1 resize-none rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={recording ? stopRecording : startRecording}
                disabled={voiceBusy || loading}
                className={`flex items-center justify-center rounded-xl border px-4 py-3 transition ${
                  recording
                    ? 'border-rose-500/50 bg-rose-500/20 text-rose-200'
                    : 'border-white/15 bg-white/5 text-cyan-300 hover:bg-white/10'
                } disabled:opacity-50`}
                title={recording ? 'Stop and transcribe' : 'Record from microphone'}
              >
                {recording ? <Square className="h-5 w-5 fill-current" /> : <Mic className={`h-5 w-5 ${voiceBusy ? 'animate-pulse' : ''}`} />}
              </button>
              <label className="flex cursor-pointer items-center justify-center rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-[10px] font-medium uppercase tracking-wide text-slate-500 hover:border-white/20 hover:text-slate-300">
                File
                <input type="file" accept="audio/*" className="hidden" onChange={onVoiceFile} disabled={voiceBusy || recording} />
              </label>
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-glow disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
                Send
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
