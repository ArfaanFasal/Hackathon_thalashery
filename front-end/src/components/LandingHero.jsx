import { motion } from 'framer-motion'
import { ArrowRight, Sparkles } from 'lucide-react'

export function LandingHero({ onStart }) {
  return (
    <div className="relative mx-auto max-w-5xl px-4 py-16 sm:py-24">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[28rem] w-[28rem] -translate-x-1/2 rounded-full bg-indigo-600/25 blur-3xl" />
      <div className="pointer-events-none absolute right-0 bottom-0 h-64 w-64 rounded-full bg-fuchsia-600/20 blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative text-center"
      >
        <p className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs font-medium text-cyan-200">
          <Sparkles className="h-3.5 w-3.5" />
          Intent-aware civic helpdesk · Voice & text · English output from Malayalam speech
        </p>
        <h1 className="bg-gradient-to-br from-white via-slate-100 to-cyan-200/90 bg-clip-text text-4xl font-bold leading-tight tracking-tight text-transparent sm:text-5xl lg:text-6xl">
          Smarter conversations for{' '}
          <span className="bg-gradient-to-r from-fuchsia-400 to-cyan-400 bg-clip-text text-transparent">civic life</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-base text-slate-400 sm:text-lg">
          Talk naturally—no rigid forms. CivicSafe figures out whether you need a service, want to flag a complaint, or
          something feels off. Malayalam voice is transcribed and translated to English for consistent intent detection.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <button
            type="button"
            onClick={onStart}
            className="group inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-cyan-500 to-indigo-600 px-8 py-3.5 text-sm font-semibold text-white shadow-glow transition hover:brightness-110"
          >
            Start conversation
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </button>
          <span className="text-sm text-slate-500">Guidance only—we never submit to government systems for you.</span>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="relative mt-16 grid gap-6 sm:grid-cols-3"
      >
        {[
          { k: 'Intent-first', v: 'Service · complaint · scam · info', c: 'from-cyan-500/20 to-transparent' },
          { k: 'Voice', v: 'Record Malayalam → English understanding', c: 'from-fuchsia-500/20 to-transparent' },
          { k: 'Dashboards', v: 'Complaints, trends, hotspots', c: 'from-emerald-500/20 to-transparent' },
        ].map((s) => (
          <div
            key={s.k}
            className={`rounded-2xl border border-white/10 bg-gradient-to-b ${s.c} p-6 text-left backdrop-blur`}
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{s.k}</p>
            <p className="mt-2 text-sm font-medium text-white">{s.v}</p>
          </div>
        ))}
      </motion.div>
    </div>
  )
}
