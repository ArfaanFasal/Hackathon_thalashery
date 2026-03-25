import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BarChart3,
  Building2,
  FolderTree,
  LayoutDashboard,
  MessageCircle,
  Network,
  Search,
  Shield,
  Bell,
  X,
  Home,
  User,
} from 'lucide-react'
import { ChatAssistant } from './components/ChatAssistant'
import { DashboardHome } from './components/DashboardHome'
import { AnalyticsView } from './components/AnalyticsView'
import { AllocationExplorer } from './components/AllocationExplorer'
import { ForwardedNetwork } from './components/ForwardedNetwork'
import { CitizenPage, DepartmentPage, AdminPage } from './components/StakeholderPages'
import { LandingHero } from './components/LandingHero'
import { API_BASE } from './lib/api'

const nav = [
  { id: 'chat', label: 'Assistant', icon: MessageCircle },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'allocation', label: 'Allocation', icon: FolderTree },
  { id: 'forwarded', label: 'Forwarded', icon: Network },
  { id: 'analytics', label: 'Map', icon: BarChart3 },
  { id: 'citizen', label: 'Citizen', icon: User },
  { id: 'department', label: 'Department', icon: Building2 },
  { id: 'admin', label: 'Admin', icon: Shield },
]

const sampleNotifications = [
  { id: 1, title: 'High-urgency complaint pattern', body: 'Review water shortage cases in the last session.', time: 'Just now' },
  { id: 2, title: 'Voice STT ready', body: 'Malayalam recordings are translated to English when OpenAI is configured.', time: '2m ago' },
  { id: 3, title: 'MongoDB sync', body: 'Chat history persists when MONGODB_URI is set.', time: '5m ago' },
]

export default function App() {
  const [screen, setScreen] = useState('landing')
  const [view, setView] = useState('chat')
  const [notifOpen, setNotifOpen] = useState(false)
  const [health, setHealth] = useState(null)
  const notifRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null))
  }, [])

  useEffect(() => {
    const onDoc = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false)
    }
    document.addEventListener('click', onDoc)
    return () => document.removeEventListener('click', onDoc)
  }, [])

  const enterApp = useCallback(() => setScreen('app'), [])

  if (screen === 'landing') {
    return (
      <div className="app-root min-h-screen text-slate-100">
        <header className="flex items-center justify-between px-4 py-5 sm:px-10">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 shadow-glow">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-white">CivicSafe AI</span>
          </div>
          <nav className="hidden items-center gap-8 text-sm text-slate-400 md:flex">
            <span className="cursor-pointer hover:text-white">About</span>
            <span className="cursor-pointer hover:text-white">Features</span>
            <span className="cursor-pointer text-cyan-300">Assistant</span>
            <span className="cursor-pointer hover:text-white">Contact</span>
          </nav>
          <button
            type="button"
            onClick={enterApp}
            className="rounded-full border border-white/20 px-5 py-2 text-sm font-medium text-white transition hover:border-cyan-400/50 hover:bg-white/5"
          >
            Open app →
          </button>
        </header>
        <LandingHero onStart={enterApp} />
      </div>
    )
  }

  return (
    <div className="app-root flex min-h-screen text-slate-100">
      <aside className="fixed left-0 top-0 z-40 flex h-full w-[4.5rem] flex-col items-center border-r border-white/10 bg-black/50 py-8 backdrop-blur-xl sm:w-20">
        <button
          type="button"
          title="Home"
          onClick={() => setScreen('landing')}
          className="mb-6 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-400 transition hover:border-cyan-500/30 hover:text-white"
        >
          <Home className="h-5 w-5" />
        </button>
        <div className="mb-8 flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500 to-indigo-600 shadow-glow">
          <Shield className="h-6 w-6 text-white" />
        </div>
        <nav className="flex flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden py-1">
          {nav.map((item) => {
            const Icon = item.icon
            const active = view === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setView(item.id)}
                title={item.label}
                className={`group relative flex h-12 w-12 items-center justify-center rounded-2xl border transition ${
                  active
                    ? 'border-cyan-400/50 bg-cyan-500/20 text-cyan-200 shadow-[0_0_24px_-4px_rgba(34,211,238,0.5)]'
                    : 'border-transparent text-slate-500 hover:border-white/10 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <Icon className="h-5 w-5" />
                {active ? (
                  <span className="absolute -right-1 top-1/2 h-8 w-1 -translate-y-1/2 rounded-full bg-cyan-400" />
                ) : null}
              </button>
            )
          })}
        </nav>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col pl-[4.5rem] sm:pl-20">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-white/10 bg-black/40 px-4 py-4 backdrop-blur-xl sm:px-8">
          <div className="hidden flex-wrap items-center gap-2 sm:flex">
            {['Overview', 'Monitoring', 'Support'].map((t, i) => (
              <span
                key={t}
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  i === 0 ? 'bg-white/10 text-white' : 'text-slate-500 hover:bg-white/5 hover:text-slate-300'
                }`}
              >
                {t}
              </span>
            ))}
          </div>
          <div className="relative hidden max-w-md flex-1 md:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="search"
              placeholder="Search sessions, issue types…"
              className="w-full rounded-full border border-white/10 bg-white/5 py-2 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-cyan-500/40 focus:outline-none"
              readOnly
            />
          </div>
          <div className="flex flex-1 items-center justify-end gap-2 sm:flex-none md:gap-3">
            {health?.chat_storage ? (
              <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium uppercase text-emerald-300 sm:inline">
                DB: {health.chat_storage}
              </span>
            ) : null}
            {health ? (
              <span
                className={`hidden rounded-full px-2 py-0.5 text-[10px] font-medium uppercase sm:inline ${
                  (health.openai_configured ?? health.gemini_configured)
                    ? 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-200'
                    : 'border border-amber-500/30 bg-amber-500/10 text-amber-200'
                }`}
              >
                STT:{' '}
                {(health.openai_configured ?? health.gemini_configured)
                  ? `OpenAI ${health.openai_model ?? health.gemini_model}`
                  : 'Demo mode'}
              </span>
            ) : null}
            <div className="relative" ref={notifRef}>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  setNotifOpen((v) => !v)
                }}
                className="relative rounded-full border border-white/10 p-2 text-slate-400 transition hover:border-cyan-500/30 hover:text-white"
                aria-label="Notifications"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-black" />
              </button>
              <AnimatePresence>
                {notifOpen ? (
                  <motion.div
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    className="absolute right-0 z-50 mt-2 w-80 rounded-2xl border border-white/15 bg-slate-900/95 shadow-2xl backdrop-blur-xl"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                      <span className="text-sm font-semibold text-white">Notifications</span>
                      <button type="button" onClick={() => setNotifOpen(false)} className="rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-white">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <ul className="max-h-80 overflow-y-auto p-2">
                      {sampleNotifications.map((n) => (
                        <li key={n.id} className="rounded-xl px-3 py-2.5 text-left transition hover:bg-white/5">
                          <p className="text-sm font-medium text-white">{n.title}</p>
                          <p className="text-xs text-slate-400">{n.body}</p>
                          <p className="mt-1 text-[10px] text-slate-500">{n.time}</p>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
            <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-fuchsia-500 to-cyan-400 ring-2 ring-white/20" title="Profile" />
          </div>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-8 sm:py-8">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="mx-auto min-h-[60vh] max-w-6xl"
          >
            {view === 'chat' ? <ChatAssistant /> : null}
            {view === 'dashboard' ? <DashboardHome /> : null}
            {view === 'allocation' ? <AllocationExplorer /> : null}
            {view === 'forwarded' ? <ForwardedNetwork /> : null}
            {view === 'analytics' ? <AnalyticsView /> : null}
            {view === 'citizen' ? <CitizenPage onOpenChat={() => setView('chat')} /> : null}
            {view === 'department' ? <DepartmentPage /> : null}
            {view === 'admin' ? <AdminPage /> : null}
          </motion.div>
        </main>
      </div>
    </div>
  )
}
