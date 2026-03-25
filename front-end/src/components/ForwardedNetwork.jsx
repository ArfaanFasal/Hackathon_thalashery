import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Clock3, LoaderCircle, Send, ShieldCheck } from 'lucide-react'
import { fetchAllocationTree } from '../lib/api'

function statusMeta(status) {
  if (status === 'completed') {
    return { icon: CheckCircle2, cls: 'text-emerald-300 bg-emerald-500/15', label: 'Completed' }
  }
  if (status === 'in_progress') {
    return { icon: LoaderCircle, cls: 'text-amber-300 bg-amber-500/15', label: 'In progress' }
  }
  return { icon: Clock3, cls: 'text-slate-300 bg-white/10', label: 'Pending' }
}

export function ForwardedNetwork() {
  const [tree, setTree] = useState(null)
  const [selected, setSelected] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [err, setErr] = useState(null)

  useEffect(() => {
    fetchAllocationTree().then(setTree).catch((e) => setErr(String(e.message)))
  }, [])

  const cases = useMemo(() => {
    if (!tree) return []
    const out = []
    for (const bucket of ['complaints', 'requests']) {
      const departments = tree[bucket] || {}
      for (const dept of Object.keys(departments)) {
        for (const item of departments[dept] || []) {
          out.push({ ...item, bucket, dept })
        }
      }
    }
    return out
      .filter((x) => x.status !== 'completed')
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
      .slice(0, 20)
  }, [tree])

  useEffect(() => {
    if (!selected && cases.length) {
      setSelected(cases[0])
    }
  }, [cases, selected])

  useEffect(() => {
    if (!selected) return
    const stat = statusMeta(selected.status || 'pending').label
    setMessages([
      {
        id: 'm1',
        by: 'bot',
        text: `Case ${selected.id} opened from ${selected.bucket}. Department: ${selected.dept}.`,
      },
      {
        id: 'm2',
        by: 'bot',
        text: `Verification packet prepared. Current authority status: ${stat}.`,
      },
    ])
  }, [selected])

  const send = () => {
    const text = draft.trim()
    if (!text) return
    setMessages((m) => [...m, { id: crypto.randomUUID(), by: 'me', text }])
    setDraft('')
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          by: 'bot',
          text: 'Forward note received. Authority channel updated with verification assurance.',
        },
      ])
    }, 300)
  }

  if (err) return <p className="text-rose-300">{err}</p>
  if (!tree) return <p className="text-slate-400">Loading forwarded network…</p>

  return (
    <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="glass-panel rounded-2xl p-4">
        <h3 className="text-sm font-semibold text-white">Forward queue</h3>
        <p className="mb-3 text-xs text-slate-500">Pending / in-progress requests and complaints for authority approval.</p>
        <ul className="max-h-[32rem] space-y-2 overflow-y-auto pr-1">
          {cases.length === 0 ? <li className="text-sm text-slate-500">No forwarded items.</li> : null}
          {cases.map((c) => {
            const meta = statusMeta(c.status || 'pending')
            const Icon = meta.icon
            return (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSelected(c)}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    selected?.id === c.id ? 'border-cyan-400/40 bg-cyan-500/10' : 'border-white/10 bg-white/5 hover:border-white/20'
                  }`}
                >
                  <p className="truncate text-sm font-medium text-white">{c.item_title || c.id}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{c.dept}</p>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase text-slate-300">{c.bucket}</span>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] uppercase ${meta.cls}`}>
                      <Icon className="h-3.5 w-3.5" />
                      {meta.label}
                    </span>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="glass-panel flex min-h-[32rem] flex-col rounded-2xl p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Forwarded Network</h3>
            <p className="text-xs text-slate-500">Authority collaboration channel (demo)</p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] uppercase text-emerald-200">
            <ShieldCheck className="h-3.5 w-3.5" />
            verified packet
          </span>
        </div>
        <div className="mb-3 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-slate-300">
          {selected ? (
            <>
              <p className="font-medium text-white">{selected.item_title || selected.id}</p>
              <p>{selected.summary || 'No summary provided.'}</p>
            </>
          ) : (
            <p>Select an item from queue.</p>
          )}
        </div>
        <div className="flex-1 space-y-2 overflow-y-auto rounded-xl border border-white/10 bg-black/30 p-3">
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.by === 'me' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs ${m.by === 'me' ? 'bg-cyan-600/70 text-white' : 'bg-white/10 text-slate-200'}`}>
                {m.text}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => (e.key === 'Enter' ? send() : null)}
            className="flex-1 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500/40 focus:outline-none"
            placeholder="Type update to authorities..."
          />
          <button type="button" onClick={send} className="rounded-xl bg-cyan-600/90 px-3 text-white">
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

