import { useState, useEffect } from 'react'
import { X, CheckCircle2, AlertCircle, Loader2, Sparkles, ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react'
import { checkHealth } from '@/api/groups'
import type { AppSettings, Group, Subject } from '@/types'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
  settings: AppSettings
  groups?: Group[]
  subjects: Subject[]
  onSave: (settings: AppSettings) => void
  onBranchSelect?: (branchCode: string) => void
}

export default function SettingsModal({
  open,
  onClose,
  settings,
  groups = [],
  subjects,
  onSave,
  onBranchSelect,
}: SettingsModalProps) {
  const [activeSubject, setActiveSubject] = useState(settings.activeSubject)
  const [selectedBranch, setSelectedBranch] = useState(settings.branchCode || 'CSE_AIML')
  const [apiKey, setApiKey] = useState(settings.apiKey)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [validating, setValidating] = useState(false)
  const [valid, setValid] = useState<boolean | null>(null)

  useEffect(() => {
    setApiKey(settings.apiKey)
    setActiveSubject(settings.activeSubject)
    setSelectedBranch(settings.branchCode || 'CSE_AIML')
  }, [settings, open])

  const handleBranchChange = (branchCode: string) => {
    setSelectedBranch(branchCode)
    if (onBranchSelect) {
      onBranchSelect(branchCode)
    }
  }

  const validate = async () => {
    if (!apiKey.trim()) return
    setValidating(true)
    setValid(null)
    localStorage.setItem('study_api_key', apiKey)
    try {
      await checkHealth()
      setValid(true)
    } catch {
      setValid(false)
    } finally {
      setValidating(false)
    }
  }

  const save = () => {
    localStorage.setItem('study_api_key', apiKey)
    localStorage.setItem('study_active_subject', activeSubject)
    onSave({ ...settings, apiKey, activeSubject, branchCode: selectedBranch })
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-[#111] border border-[#2a2a2a] rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#222]">
          <div>
            <h2 className="text-sm font-semibold text-white">Study Environment & Department</h2>
            <p className="text-[11px] text-[#6a6a6a]">Select your branch and study subjects</p>
          </div>
          <button onClick={onClose} className="text-[#5a5a5a] hover:text-white transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
          {/* AI Backend Status Card */}
          <div className="p-3 rounded-xl bg-gradient-to-r from-[#191932] to-[#12121e] border border-[#3D46E8]/30 flex items-start gap-3">
            <div className="p-1.5 rounded-lg bg-[#3D46E8]/20 text-[#B18CFF] shrink-0 mt-0.5">
              <Sparkles size={14} />
            </div>
            <div className="text-xs">
              <div className="font-medium text-white flex items-center gap-1.5">
                AI Engine: Google Gemini 3.5 Flash
                <ShieldCheck size={13} className="text-emerald-400" />
              </div>
              <p className="text-[#8a8a9a] text-[11px] mt-0.5 leading-relaxed">
                Your Google API key runs securely on the FastAPI backend (<code className="text-[#B18CFF]">.env</code>). No external AI key is required from your browser.
              </p>
            </div>
          </div>

          {/* Department / Branch Selector */}
          <div>
            <label className="text-xs font-medium text-[#b0b0b0] mb-1.5 block">
              Department / Class Community
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleBranchChange('CSE_AIML')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedBranch === 'CSE_AIML'
                    ? 'bg-[#3D46E8]/20 border-[#3D46E8] text-white'
                    : 'bg-[#161616] border-[#262626] text-[#888] hover:border-[#383838]'
                }`}
              >
                <div className="text-xs font-semibold">CSE AIML</div>
                <div className="text-[10px] text-[#a0a0a0] mt-0.5">AI & Machine Learning</div>
                <div className="text-[9px] text-[#B18CFF] font-mono mt-1">Tenant: CSE_AIML</div>
              </button>

              <button
                type="button"
                onClick={() => handleBranchChange('CSE_CORE')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedBranch === 'CSE_CORE'
                    ? 'bg-[#3D46E8]/20 border-[#3D46E8] text-white'
                    : 'bg-[#161616] border-[#262626] text-[#888] hover:border-[#383838]'
                }`}
              >
                <div className="text-xs font-semibold">CSE Core</div>
                <div className="text-[10px] text-[#a0a0a0] mt-0.5">Core Engineering</div>
                <div className="text-[9px] text-[#B18CFF] font-mono mt-1">Tenant: CSE_CORE</div>
              </button>
            </div>
          </div>

          {/* Active Subject */}
          <div>
            <label className="text-xs font-medium text-[#b0b0b0] mb-1.5 block">
              Default Subject
            </label>
            <select
              value={activeSubject}
              onChange={(e) => setActiveSubject(e.target.value)}
              className="w-full bg-[#161616] border border-[#262626] rounded-xl px-3 py-2.5
                         text-xs text-[#f0f0f0] focus:outline-none focus:border-[#3D46E8]"
            >
              {subjects.map((s) => (
                <option key={s.id} value={s.subject_code}>
                  {s.name} ({s.subject_code})
                </option>
              ))}
            </select>
          </div>

          {/* Advanced / Developer Accordion */}
          <div className="border-t border-[#222] pt-3">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center justify-between w-full text-[11px] text-[#6a6a6a] hover:text-[#9a9a9a] transition-colors"
            >
              <span>Developer / Multi-Tenant Key</span>
              {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            {showAdvanced && (
              <div className="mt-3 space-y-2 bg-[#161616] p-3 rounded-xl border border-[#222]">
                <p className="text-[10px] text-[#7a7a7a]">
                  This internal key (<code className="text-[#a0a0a0]">X-API-Key</code>) maps requests to the tenant SQLite group. It is NOT your Google Gemini key.
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={apiKey}
                    onChange={(e) => { setApiKey(e.target.value); setValid(null) }}
                    className="flex-1 px-3 py-1.5 bg-[#111] border border-[#2a2a2a] rounded-lg text-xs font-mono text-[#f0f0f0] focus:outline-none"
                  />
                  <button
                    onClick={validate}
                    disabled={validating || !apiKey.trim()}
                    className="px-3 py-1.5 text-xs bg-[#222] hover:bg-[#2c2c2c] text-white rounded-lg disabled:opacity-40"
                  >
                    {validating ? <Loader2 size={12} className="animate-spin" /> : 'Test'}
                  </button>
                </div>
                {valid === true && (
                  <div className="flex items-center gap-1 text-[11px] text-emerald-400">
                    <CheckCircle2 size={11} /> Key valid & backend reachable
                  </div>
                )}
                {valid === false && (
                  <div className="flex items-center gap-1 text-[11px] text-red-400">
                    <AlertCircle size={11} /> Invalid tenant key or backend unreachable
                  </div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={save}
            className="w-full py-2.5 bg-[#3D46E8] hover:bg-[#5D68FF] text-white text-xs
                       font-semibold rounded-xl transition-colors shadow-lg shadow-[#3D46E8]/25"
          >
            Apply & Continue
          </button>
        </div>
      </div>
    </div>
  )
}
