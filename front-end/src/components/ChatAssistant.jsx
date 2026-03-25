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
    const text = result?.converted_text || ''
    setInput((prev) => (prev ? `${prev} ${text}` : text).trim())
    setVoiceStatus({
      tone: result?.mode === 'live' ? 'ok' : 'warn',
      text: result?.mode === 'live'
        ? 'Live Gemini transcription completed.'
        : result?.detail || 'Demo transcription mode is active.',
    })
  }

  const onSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    runTurn({ message: input })
  }

  const startRecording = async () => {
    if (recording || voiceBusy) return
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
      <div className="glass-panel mb-4 flex shrink-0 items-center justify-between rounded-2xl px-5 py-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-emerald-300/90">Assistant</p>
          <h2 className="text-lg font-semibold text-white">Natural conversation and complaint intelligence</h2>
          <p className="text-sm text-slate-400">
            Speak naturally and the backend will extract issue, category, department, duration, priority, and cluster signals.
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
              placeholder="Type here, or use the mic to capture a complaint..."
              className="min-h-[3rem] flex-1 resize-none rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
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
