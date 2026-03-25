import { MessageCircle, Building2, Shield } from 'lucide-react'

export function CitizenPage({ onOpenChat }) {
  return (
    <div className="mx-auto max-w-xl space-y-6 text-center">
      <div className="glass-panel rounded-3xl p-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500 to-teal-600">
          <MessageCircle className="h-7 w-7 text-white" />
        </div>
        <h2 className="mt-6 text-2xl font-semibold text-white">Citizen</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Report outages, ask for new connections, or check steps for documents. Use voice in your language—Whisper will transcribe it when the API is configured.
        </p>
        <button
          type="button"
          onClick={onOpenChat}
          className="mt-8 w-full rounded-2xl bg-gradient-to-r from-cyan-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-glow transition hover:opacity-95"
        >
          Open assistant
        </button>
      </div>
    </div>
  )
}

export function DepartmentPage() {
  return (
    <div className="mx-auto max-w-xl space-y-6 text-center">
      <div className="glass-panel rounded-3xl p-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600">
          <Building2 className="h-7 w-7 text-white" />
        </div>
        <h2 className="mt-6 text-2xl font-semibold text-white">Department desk</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Use Case allocation (sidebar) to browse complaints and requests by department. The dashboard shows priority mix and department load from saved records.
        </p>
      </div>
    </div>
  )
}

export function AdminPage() {
  return (
    <div className="mx-auto max-w-xl space-y-6 text-center">
      <div className="glass-panel rounded-3xl p-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-rose-600">
          <Shield className="h-7 w-7 text-white" />
        </div>
        <h2 className="mt-6 text-2xl font-semibold text-white">Admin</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Records persist in SQLite under <span className="font-mono text-xs text-slate-500">data/civicsafe_records.sqlite</span>. Allocation folders mirror complaint vs request type and department with status tracking.
        </p>
      </div>
    </div>
  )
}
