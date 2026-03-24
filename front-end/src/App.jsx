import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Banknote,
  Building2,
  CircleAlert,
  FileCheck2,
  Home,
  LoaderCircle,
  MessageSquareWarning,
  Send,
  ShieldAlert,
  UserRound,
} from 'lucide-react'

const serviceFlow = {
  'Government Services': {
    icon: Building2,
    options: ['Aadhaar Services', 'PAN Services', 'Electricity Services', 'Water Services', 'Passport Services'],
  },
  'Banking Services': {
    icon: Banknote,
    options: ['Loan Application', 'Account Opening', 'KYC Update', 'Credit Card Services'],
  },
  'Personal Services': {
    icon: UserRound,
    options: ['Document Notarization', 'Insurance Enrollment', 'Address Change Help'],
  },
}

const complaintFlow = {
  'Government Complaints': {
    icon: Building2,
    options: ['Electricity Issue', 'Water Issue', 'Road Issue', 'Waste Management'],
  },
  'Banking Complaints': {
    icon: Banknote,
    options: ['Transaction Issue', 'Fraud Complaint', 'Account Issue'],
  },
  'Personal Complaints': {
    icon: UserRound,
    options: ['Delivery Issue', 'Service Delay', 'Other'],
  },
}

const serviceDetails = {
  default: {
    documents: ['Government-issued photo ID', 'Recent proof of address', 'Application form'],
    steps: ['Select the service and verify eligibility', 'Upload or submit required documents', 'Track request status and complete verification'],
    website: 'https://official-service-portal.example',
  },
}

const fadeSlide = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.28, ease: 'easeOut' },
}

function App() {
  const [activeTab, setActiveTab] = useState(null)
  const [serviceCategory, setServiceCategory] = useState('')
  const [selectedService, setSelectedService] = useState('')
  const [complaintCategory, setComplaintCategory] = useState('')
  const [complaintType, setComplaintType] = useState('')
  const [complaintText, setComplaintText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedComplaint, setSubmittedComplaint] = useState(null)

  const complaintOutput = useMemo(() => {
    if (!submittedComplaint) return null
    const urgency = /fraud|urgent|emergency|immediately|critical/i.test(submittedComplaint.description)
      ? 'High'
      : submittedComplaint.description.length > 80
        ? 'Medium'
        : 'Low'
    return { ...submittedComplaint, urgency }
  }, [submittedComplaint])

  const handleTabClick = (tab) => {
    setActiveTab(tab)
    if (tab === 'services') {
      setComplaintCategory('')
      setComplaintType('')
      setComplaintText('')
      setSubmittedComplaint(null)
    } else {
      setServiceCategory('')
      setSelectedService('')
    }
  }

  const handleSubmitComplaint = async () => {
    if (!complaintType || !complaintText.trim()) return
    setIsSubmitting(true)
    await new Promise((resolve) => setTimeout(resolve, 1200))
    setSubmittedComplaint({
      issue: complaintType,
      description: complaintText.trim(),
      location: 'Not specified',
    })
    setIsSubmitting(false)
  }

  const selectedServiceInfo = serviceDetails[selectedService] || serviceDetails.default

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="rounded-3xl border border-cyan-100 bg-white/80 p-8 shadow-soft backdrop-blur sm:p-10"
      >
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold tracking-wide text-cyan-700">
              <ShieldAlert size={14} /> Citizen Support Platform
            </p>
            <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">CivicSafe AI</h1>
            <p className="mt-2 text-base text-slate-600 sm:text-lg">Smart Citizen Assistant & Scam Shield</p>
          </div>
          <Home className="hidden text-cyan-500 sm:block" size={34} />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <motion.button
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleTabClick('services')}
            className={`rounded-2xl border p-6 text-left transition-all ${
              activeTab === 'services'
                ? 'border-cyan-300 bg-cyan-50 shadow-soft'
                : 'border-slate-200 bg-white hover:border-cyan-200 hover:shadow-soft'
            }`}
          >
            <div className="mb-3 inline-flex rounded-xl bg-cyan-100 p-3 text-cyan-700">
              <FileCheck2 size={22} />
            </div>
            <h2 className="text-2xl font-semibold text-slate-900">Services</h2>
            <p className="mt-1 text-sm text-slate-600">Browse service categories with guided document and process steps.</p>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleTabClick('complaints')}
            className={`rounded-2xl border p-6 text-left transition-all ${
              activeTab === 'complaints'
                ? 'border-emerald-300 bg-emerald-50 shadow-soft'
                : 'border-slate-200 bg-white hover:border-emerald-200 hover:shadow-soft'
            }`}
          >
            <div className="mb-3 inline-flex rounded-xl bg-emerald-100 p-3 text-emerald-700">
              <MessageSquareWarning size={22} />
            </div>
            <h2 className="text-2xl font-semibold text-slate-900">Complaints</h2>
            <p className="mt-1 text-sm text-slate-600">Submit structured complaints with quick categorization and urgency flags.</p>
          </motion.button>
        </div>
      </motion.section>

      <AnimatePresence mode="wait">
        {activeTab === 'services' && (
          <motion.section key="services" {...fadeSlide} className="mt-6 rounded-3xl border border-cyan-100 bg-white/90 p-6 shadow-soft sm:p-8">
            <h3 className="text-xl font-semibold text-slate-900">Services Flow</h3>
            <p className="mt-1 text-sm text-slate-600">Select a category and service to view documents and process steps.</p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Service Category</label>
                <select
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-200"
                  value={serviceCategory}
                  onChange={(e) => {
                    setServiceCategory(e.target.value)
                    setSelectedService('')
                  }}
                >
                  <option value="">Choose category</option>
                  {Object.keys(serviceFlow).map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              {serviceCategory && (
                <motion.div {...fadeSlide}>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Service Type</label>
                  <select
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-200"
                    value={selectedService}
                    onChange={(e) => setSelectedService(e.target.value)}
                  >
                    <option value="">Choose service</option>
                    {serviceFlow[serviceCategory].options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </motion.div>
              )}
            </div>

            {selectedService && (
              <motion.div {...fadeSlide} className="mt-6 grid gap-4 md:grid-cols-3">
                <article className="rounded-2xl border border-slate-200 bg-white p-5">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Required Documents</h4>
                  <ul className="space-y-2 text-sm text-slate-700">
                    {selectedServiceInfo.documents.map((doc) => (
                      <li key={doc} className="flex items-start gap-2">
                        <CircleAlert size={16} className="mt-0.5 text-cyan-600" />
                        <span>{doc}</span>
                      </li>
                    ))}
                  </ul>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-white p-5">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Step-by-Step Process</h4>
                  <ol className="list-decimal space-y-2 pl-4 text-sm text-slate-700">
                    {selectedServiceInfo.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </article>
                <article className="rounded-2xl border border-slate-200 bg-white p-5">
                  <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Official Website</h4>
                  <a
                    href={selectedServiceInfo.website}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-700"
                  >
                    Visit Portal
                  </a>
                </article>
              </motion.div>
            )}
          </motion.section>
        )}

        {activeTab === 'complaints' && (
          <motion.section key="complaints" {...fadeSlide} className="mt-6 rounded-3xl border border-emerald-100 bg-white/90 p-6 shadow-soft sm:p-8">
            <h3 className="text-xl font-semibold text-slate-900">Complaints Flow</h3>
            <p className="mt-1 text-sm text-slate-600">Choose complaint type, describe your issue, and get a structured summary.</p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Complaint Category</label>
                <select
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-200"
                  value={complaintCategory}
                  onChange={(e) => {
                    setComplaintCategory(e.target.value)
                    setComplaintType('')
                  }}
                >
                  <option value="">Choose category</option>
                  {Object.keys(complaintFlow).map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              {complaintCategory && (
                <motion.div {...fadeSlide}>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Complaint Type</label>
                  <select
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-200"
                    value={complaintType}
                    onChange={(e) => setComplaintType(e.target.value)}
                  >
                    <option value="">Choose complaint type</option>
                    {complaintFlow[complaintCategory].options.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </motion.div>
              )}
            </div>

            {complaintType && (
              <motion.div {...fadeSlide} className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
                <label className="mb-2 block text-sm font-medium text-slate-700">Describe your issue</label>
                <textarea
                  value={complaintText}
                  onChange={(e) => setComplaintText(e.target.value)}
                  placeholder="Describe what happened, when it happened, and expected resolution..."
                  className="h-28 w-full resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-200"
                />
                <motion.button
                  whileTap={{ scale: 0.97 }}
                  onClick={handleSubmitComplaint}
                  disabled={isSubmitting || !complaintText.trim()}
                  className="mt-4 inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isSubmitting ? <LoaderCircle size={16} className="animate-spin" /> : <Send size={16} />}
                  {isSubmitting ? 'Processing...' : 'Submit'}
                </motion.button>
              </motion.div>
            )}

            {complaintOutput && (
              <motion.div {...fadeSlide} className="mt-6 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Structured Output</h4>
                <div className="mt-3 grid gap-3 text-sm text-slate-700 sm:grid-cols-3">
                  <p><span className="font-semibold">Issue:</span> {complaintOutput.issue}</p>
                  <p><span className="font-semibold">Location:</span> {complaintOutput.location}</p>
                  <p><span className="font-semibold">Urgency:</span> {complaintOutput.urgency}</p>
                </div>
              </motion.div>
            )}
          </motion.section>
        )}
      </AnimatePresence>
    </main>
  )
}

export default App
