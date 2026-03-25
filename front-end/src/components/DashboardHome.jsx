import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Bar, BarChart, Cell, Pie, PieChart, Tooltip, XAxis, YAxis } from 'recharts'
import { Activity, AlertTriangle, FileInput, ShieldAlert, Sparkles } from 'lucide-react'
import { fetchDashboard } from '../lib/api'

const PIE_COLORS = ['#22d3ee', '#818cf8', '#f59e0b', '#34d399', '#fb7185', '#a78bfa']

const toSeries = (obj = {}) => Object.entries(obj).map(([name, value]) => ({ name, value }))

export function DashboardHome() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((e) => setErr(String(e.message)))
  }, [])

  if (err) return <p className="text-rose-300">{err}</p>
  if (!data) return <p className="text-slate-400">Loading dashboard...</p>

  const { dashboard: d } = data
  const priorityData = toSeries(d.complaints_by_priority)
  const departmentData = toSeries(d.complaints_by_department).slice(0, 8)
  const requests = d.total_requests ?? 0

  return (
    <div className="space-y-6">
      <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass-panel rounded-3xl p-8">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            { label: 'Complaints', value: d.total_complaints, icon: Activity },
            { label: 'Requests & services', value: requests, icon: FileInput },
            { label: 'High urgency', value: d.high_urgency_count, icon: AlertTriangle },
            { label: 'Scam checks', value: d.total_scam_checks, icon: ShieldAlert },
            { label: 'Clusters', value: d.total_clusters, icon: Sparkles },
          ].map((item) => (
            <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <item.icon className="h-5 w-5 text-cyan-300" />
              <p className="mt-3 text-2xl font-bold text-white">{item.value}</p>
              <p className="text-xs uppercase tracking-wide text-slate-400">{item.label}</p>
            </div>
          ))}
        </div>
      </motion.section>

      <div className="mx-auto grid max-w-4xl gap-8 lg:grid-cols-2">
        <div className="glass-panel min-w-0 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white">Priority distribution</h3>
          <p className="text-xs text-slate-500">Complaints by priority band</p>
          <div className="mt-4 h-64 min-w-0 overflow-x-auto">
            <PieChart width={360} height={240}>
                <Pie
                  data={priorityData.length ? priorityData : [{ name: 'No data', value: 1 }]}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={52}
                  outerRadius={80}
                >
                  {(priorityData.length ? priorityData : [{ name: 'No data', value: 1 }]).map((entry, index) => (
                    <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
            </PieChart>
          </div>
        </div>

        <div className="glass-panel min-w-0 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white">Department load</h3>
          <p className="text-xs text-slate-500">Narrow bars — top departments</p>
          <div className="mt-4 h-64 min-w-0 overflow-x-auto">
              <BarChart
                width={560}
                height={240}
                data={departmentData.length ? departmentData : [{ name: 'No data', value: 0 }]}
                barSize={18}
                maxBarSize={22}
                barGap={4}
                categoryGap={28}
                margin={{ left: 4, right: 8, top: 8, bottom: 32 }}
              >
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  angle={-18}
                  textAnchor="end"
                  height={56}
                />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
                <Tooltip />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="#22d3ee" />
              </BarChart>
          </div>
        </div>
      </div>
    </div>
  )
}
