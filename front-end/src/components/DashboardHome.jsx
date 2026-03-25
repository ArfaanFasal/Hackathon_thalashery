import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Activity, AlertTriangle, Building2, ShieldAlert, Sparkles } from 'lucide-react'
import { fetchDashboard } from '../lib/api'

const PIE_COLORS = ['#22d3ee', '#818cf8', '#f59e0b', '#34d399', '#fb7185', '#a78bfa']

const dashTabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'priority', label: 'Priority' },
  { id: 'departments', label: 'Departments' },
]

const toSeries = (obj = {}) => Object.entries(obj).map(([name, value]) => ({ name, value }))

export function DashboardHome() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [dashTab, setDashTab] = useState('overview')

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((e) => setErr(String(e.message)))
  }, [])

  if (err) return <p className="text-rose-300">{err}</p>
  if (!data) return <p className="text-slate-400">Loading dashboard...</p>

  const { dashboard: d } = data
  const typeData = toSeries(d.complaints_by_type)
  const priorityData = toSeries(d.complaints_by_priority)
  const departmentData = toSeries(d.complaints_by_department).slice(0, 6)
  const complaintTypeData = toSeries(d.complaints_by_complaint_type)
  const timeline = d.priority_timeline?.length ? d.priority_timeline : [{ date: 'Today', High: 0, Medium: 0, Low: 0 }]
  const alerts = d.cluster_alerts || []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-1 rounded-2xl border border-white/10 bg-black/30 p-1">
          {dashTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setDashTab(tab.id)}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                dashTab === tab.id
                  ? 'bg-gradient-to-r from-cyan-600/80 to-indigo-600/80 text-white shadow-glow'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass-panel rounded-3xl p-8">
        <div className="grid gap-3 md:grid-cols-4">
          {[
            { label: 'Complaints', value: d.total_complaints, icon: Activity },
            { label: 'High priority', value: d.high_urgency_count, icon: AlertTriangle },
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

      <div className="grid gap-6 lg:grid-cols-2">
        {(dashTab === 'overview' || dashTab === 'priority') ? (
          <div className="glass-panel rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-white">Priority distribution</h3>
            <p className="text-xs text-slate-500">Quick view of low, medium, and high cases</p>
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={priorityData.length ? priorityData : [{ name: 'No data', value: 1 }]} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90}>
                    {(priorityData.length ? priorityData : [{ name: 'No data', value: 1 }]).map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : null}

        {(dashTab === 'overview' || dashTab === 'departments') ? (
          <div className="glass-panel rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-white">Department load</h3>
            <p className="text-xs text-slate-500">Which department is receiving the most issues</p>
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={departmentData.length ? departmentData : [{ name: 'No data', value: 0 }]}>
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} interval={0} angle={-12} height={60} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#22d3ee" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-panel rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white">Priority trend</h3>
          <p className="text-xs text-slate-500">Daily complaint mix by urgency level</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="High" stroke="#f59e0b" strokeWidth={3} />
                <Line type="monotone" dataKey="Medium" stroke="#22d3ee" strokeWidth={3} />
                <Line type="monotone" dataKey="Low" stroke="#34d399" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white">Complaint intake types</h3>
          <p className="text-xs text-slate-500">Service request, grievance, emergency, or certificate request</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={complaintTypeData.length ? complaintTypeData : [{ name: 'No data', value: 0 }]}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#818cf8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="glass-panel rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white">Issue category split</h3>
          <p className="text-xs text-slate-500">Most common complaint issues in the current demo session</p>
          <div className="mt-4 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeData.length ? typeData : [{ name: 'No data', value: 0 }]}>
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} interval={0} angle={-12} height={60} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {(typeData.length ? typeData : [{ name: 'No data', value: 0 }]).map((entry, index) => (
                    <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-cyan-300" />
            <h3 className="text-sm font-semibold text-white">Cluster alerts</h3>
          </div>
          <p className="mt-1 text-xs text-slate-500">Area-level issue groups detected by the backend</p>
          <div className="mt-4 space-y-3">
            {alerts.length === 0 ? (
              <p className="text-sm text-slate-500">No complaint clusters yet.</p>
            ) : (
              alerts.map((alert) => (
                <div key={alert.cluster_id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{alert.location}</p>
                      <p className="text-xs text-slate-400">{alert.category}</p>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${alert.priority === 'High' ? 'bg-amber-500/20 text-amber-200' : 'bg-cyan-500/20 text-cyan-200'}`}>
                      {alert.priority}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-slate-300">{alert.count} complaint(s) linked in this cluster.</p>
                  <p className="mt-1 text-[11px] text-slate-500">{alert.escalated ? 'Authority escalation suggested.' : 'Monitoring cluster growth.'}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
