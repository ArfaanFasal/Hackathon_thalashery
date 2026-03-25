import { useEffect, useState } from 'react'
import { MapPin } from 'lucide-react'
import { fetchDashboard } from '../lib/api'

export function AnalyticsView() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetchDashboard().then(setData)
  }, [])

  if (!data) return <p className="text-slate-400">Loading map view…</p>

  const { mapPoints } = data

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Geographic view</h2>
        <p className="text-sm text-slate-400">Complaint-linked locations from saved records (no extra charts here).</p>
      </div>

      <div className="glass-panel rounded-2xl p-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(mapPoints || []).map((point, index) => (
            <div
              key={`${point.location}-${index}`}
              className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4 transition hover:border-cyan-500/30"
            >
              <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-cyan-400" />
              <div>
                <p className="font-medium text-white">{point.location}</p>
                <p className="text-sm text-slate-400">{point.issue}</p>
                <p className="text-xs text-amber-200/80">Priority: {point.urgency}</p>
              </div>
            </div>
          ))}
          {(!mapPoints || mapPoints.length === 0) ? <p className="text-sm text-slate-500">No mapped complaints yet.</p> : null}
        </div>
      </div>
    </div>
  )
}
