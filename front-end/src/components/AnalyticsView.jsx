import { useEffect, useState } from 'react'
import { MapPin } from 'lucide-react'
import { Bar, BarChart, Pie, PieChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchDashboard } from '../lib/api'

const COLORS = ['#22d3ee', '#818cf8', '#34d399', '#f59e0b', '#fb7185', '#a78bfa']

const toSeries = (obj = {}) => Object.entries(obj).map(([name, value]) => ({ name, value }))

export function AnalyticsView() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetchDashboard().then(setData)
  }, [])

  if (!data) return <p className="text-slate-400">Loading...</p>

  const { dashboard: d, mapPoints } = data
  const byLoc = toSeries(d.complaints_by_location)
  const byPriority = toSeries(d.complaints_by_priority)

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-panel rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white">Complaints by location</h2>
          <p className="text-sm text-slate-400">Simple area-wise distribution for faster review.</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byLoc.length ? byLoc : [{ name: 'No data', value: 0 }]}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#22d3ee" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white">Priority mix</h2>
          <p className="text-sm text-slate-400">Pie chart view of the current complaint urgency split.</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={byPriority.length ? byPriority : [{ name: 'No data', value: 1 }]} dataKey="value" nameKey="name" outerRadius={96}>
                  {(byPriority.length ? byPriority : [{ name: 'No data', value: 1 }]).map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="glass-panel rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-white">Geographic hotspots</h2>
        <p className="text-sm text-slate-400">Coordinates map to known demo areas when mentioned in complaints.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(mapPoints || []).map((point, index) => (
            <div key={`${point.location}-${index}`} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4 transition hover:border-cyan-500/30">
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
