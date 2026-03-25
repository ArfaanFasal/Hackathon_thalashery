import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, ChevronRight, Clock3, FileText, Folder, FolderOpen, LoaderCircle } from 'lucide-react'
import { fetchAllocationTree } from '../lib/api'

const bucketLabel = { complaints: 'Complaints', requests: 'Requests' }

export function AllocationExplorer() {
  const [tree, setTree] = useState(null)
  const [err, setErr] = useState(null)
  const [bucket, setBucket] = useState(null)
  const [domain, setDomain] = useState(null)

  useEffect(() => {
    fetchAllocationTree()
      .then(setTree)
      .catch((e) => setErr(String(e.message)))
  }, [])

  if (err) return <p className="text-rose-300">{err}</p>
  if (!tree) return <p className="text-slate-400">Loading allocation folders…</p>

  const branch = bucket ? tree[bucket] || {} : {}
  const departmentKeys = Object.keys(branch)
  const records = bucket && domain ? branch[domain] || [] : []

  const StatusIcon = ({ status }) => {
    if (status === 'completed') return <CheckCircle2 className="h-4 w-4 text-emerald-300" />
    if (status === 'in_progress') return <LoaderCircle className="h-4 w-4 text-amber-300" />
    return <Clock3 className="h-4 w-4 text-slate-400" />
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Case allocation</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">
          Open a top folder (complaints or requests), then a field domain to see saved cases from the database.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <motion.div layout className="glass-panel rounded-2xl p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">1 · Type</p>
          <ul className="space-y-1">
            {['complaints', 'requests'].map((b) => (
              <li key={b}>
                <button
                  type="button"
                  onClick={() => {
                    setBucket(b)
                    setDomain(null)
                  }}
                  className={`flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm transition ${
                    bucket === b ? 'bg-cyan-500/20 text-cyan-100' : 'text-slate-300 hover:bg-white/5'
                  }`}
                >
                  {bucket === b ? <FolderOpen className="h-4 w-4 shrink-0 text-cyan-300" /> : <Folder className="h-4 w-4 shrink-0 text-slate-500" />}
                  {bucketLabel[b]}
                </button>
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div layout className="glass-panel rounded-2xl p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">2 · Department</p>
          {!bucket ? (
            <p className="text-sm text-slate-500">Choose complaints or requests first.</p>
          ) : departmentKeys.length === 0 ? (
            <p className="text-sm text-slate-500">No records in this folder yet.</p>
          ) : (
            <ul className="max-h-72 space-y-1 overflow-y-auto pr-1">
              {departmentKeys.sort().map((dk) => (
                <li key={dk}>
                  <button
                    type="button"
                    onClick={() => setDomain(dk)}
                    className={`flex w-full items-center gap-1 rounded-xl px-3 py-2 text-left text-sm transition ${
                      domain === dk ? 'bg-indigo-500/20 text-indigo-100' : 'text-slate-300 hover:bg-white/5'
                    }`}
                  >
                    <ChevronRight className="h-4 w-4 shrink-0 opacity-60" />
                    <span className="truncate text-xs">{dk}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </motion.div>

        <motion.div layout className="glass-panel rounded-2xl p-4 lg:col-span-1">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">3 · Records</p>
          {!bucket || !domain ? (
            <p className="text-sm text-slate-500">Select a domain to list cases.</p>
          ) : records.length === 0 ? (
            <p className="text-sm text-slate-500">No entries here.</p>
          ) : (
            <ul className="max-h-80 space-y-2 overflow-y-auto pr-1">
              {records.map((r) => (
                <li key={r.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="flex items-start gap-2">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400/80" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium text-white">{r.item_title || r.domain_title || r.id}</p>
                        <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase text-slate-300">
                          <StatusIcon status={r.status} />
                          {String(r.status || 'pending').replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">{r.created_at}</p>
                      {r.department ? <p className="mt-1 text-[11px] text-cyan-200/80">Dept: {r.department}</p> : null}
                      {r.summary ? <p className="mt-1 line-clamp-3 text-xs text-slate-400">{r.summary}</p> : null}
                      {r.location ? <p className="mt-1 text-[11px] text-slate-500">Location: {r.location}</p> : null}
                      {r.priority ? (
                        <span className="mt-2 inline-block rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase text-slate-300">
                          {r.priority}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </motion.div>
      </div>
    </div>
  )
}
