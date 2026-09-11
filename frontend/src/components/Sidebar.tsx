import { useState } from 'react'
import {
  Upload, Settings, ChevronDown, ChevronRight,
  FileText, Image, CheckCircle2, AlertCircle,
  Shield, BookOpen, Loader2, GraduationCap,
} from 'lucide-react'
import type { AppSettings, DocumentEntry, Group, Subject } from '@/types'

// ---------------------------------------------------------------------------
// Collapsible section wrapper
// ---------------------------------------------------------------------------
function Section({
  title, icon, defaultOpen = true, children,
}: {
  title: string
  icon: React.ReactNode
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-[#1a1a1a] last:border-0">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-[11px] font-semibold
                   tracking-wider text-[#5a5a5a] uppercase hover:text-[#8a8a8a] transition-colors"
      >
        <span className="flex items-center gap-1.5">{icon}{title}</span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && <div className="pb-1">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Document status badge
// ---------------------------------------------------------------------------
function StatusBadge({ status }: { status: DocumentEntry['status'] }) {
  switch (status) {
    case 'pending':
      return <span className="text-[10px] text-[#5a5a5a] bg-[#2a2a2a] px-1.5 py-0.5 rounded">Pending</span>
    case 'processing':
      return (
        <span className="text-[10px] text-amber-400 flex items-center gap-1">
          <Loader2 size={9} className="animate-spin" /> OCR
        </span>
      )
    case 'completed':
      return <CheckCircle2 size={11} className="text-emerald-500 shrink-0" />
    case 'failed':
      return <AlertCircle size={11} className="text-red-400 shrink-0" />
    default:
      return null
  }
}

function getFileIcon(filename: string, size = 12) {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (['jpg', 'jpeg', 'png', 'webp'].includes(ext || '')) return <Image size={size} />
  return <FileText size={size} />
}

// ---------------------------------------------------------------------------
// Subject pill (clickable to set active subject)
// ---------------------------------------------------------------------------
function SubjectPill({
  subject, active, onClick,
}: { subject: Subject; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all text-left
        ${active
          ? 'bg-[#3D46E8]/20 text-white border border-[#3D46E8]/50 font-medium'
          : 'text-[#8a8a8a] hover:bg-[#1a1a1a] hover:text-[#d0d0d0]'
        }`}
    >
      <BookOpen size={11} className={active ? 'text-[#B18CFF]' : 'text-[#4a4a4a]'} />
      <span className="truncate">{subject.name}</span>
      <span className="ml-auto text-[10px] text-[#4a4a4a]">{subject.subject_code}</span>
    </button>
  )
}

// ---------------------------------------------------------------------------
// Main Sidebar
// ---------------------------------------------------------------------------
interface SidebarProps {
  settings: AppSettings
  groups?: Group[]
  subjects: Subject[]
  documents: DocumentEntry[]
  onUploadClick: () => void
  onSettingsClick: () => void
  onSubjectSelect: (code: string) => void
  onBranchSelect?: (branchCode: string) => void
}

// Static PYQ entries for demo (in production, these come from the API)
const PYQ_PAPERS = [
  { label: '2024 End Semester', verified: true },
  { label: '2023 End Semester', verified: true },
  { label: '2022 Mid Semester', verified: true },
  { label: '2021 End Semester', verified: false },
]

export default function Sidebar({
  settings, groups = [], subjects, documents, onUploadClick, onSettingsClick, onSubjectSelect, onBranchSelect,
}: SidebarProps) {
  return (
    <aside className="flex flex-col h-full w-72 shrink-0 bg-[#0d0d0d]/80 backdrop-blur-md
                      border-r border-[#1a1a1a]">
      {/* Logo / app name */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[#1a1a1a]">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#3D46E8] to-[#B18CFF]
                        flex items-center justify-center shrink-0">
          <GraduationCap size={16} className="text-white" />
        </div>
        <div>
          <div className="text-sm font-bold text-white tracking-tight">Let'sStudy</div>
          <div className="text-[10px] text-[#4a4a4a]">RAG Study Engine</div>
        </div>
        <button
          onClick={onSettingsClick}
          className="ml-auto text-[#4a4a4a] hover:text-[#a0a0a0] transition-colors"
          title="Settings"
        >
          <Settings size={14} />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto py-3 space-y-1 min-h-0">

        {/* Active community / tenant */}
        <Section title="Active Department" icon={<Shield size={10} />} defaultOpen>
          <div className="px-3 pb-1">
            <div className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg bg-[#171717] border border-[#2a2a2a]">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-dot shrink-0" />
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-white truncate">
                    {settings.groupName || 'CSE AIML 2026'}
                  </div>
                  <div className="text-[10px] text-[#B18CFF] truncate font-mono">{settings.branchCode || 'CSE_AIML'}</div>
                </div>
              </div>

              {groups.length > 1 && onBranchSelect && (
                <select
                  value={settings.branchCode}
                  onChange={(e) => onBranchSelect(e.target.value)}
                  className="bg-[#111] border border-[#333] text-[11px] text-[#a0a0a0] rounded px-1.5 py-1 focus:outline-none focus:border-[#3D46E8] cursor-pointer"
                  title="Switch Department"
                >
                  {groups.map((g) => (
                    <option key={g.id} value={g.branch_code}>
                      {g.branch_code === 'CSE_AIML' ? 'AIML' : 'Core'}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Subject list */}
          {subjects.length > 0 && (
            <div className="px-3 pt-1 space-y-0.5">
              {subjects.map((s) => (
                <SubjectPill
                  key={s.id}
                  subject={s}
                  active={settings.activeSubject === s.subject_code}
                  onClick={() => onSubjectSelect(s.subject_code)}
                />
              ))}
            </div>
          )}
        </Section>

        <div className="border-t border-[#1a1a1a] my-1" />

        {/* PYQ Vault */}
        <Section title="Verified PYQs" icon={<Shield size={10} />} defaultOpen>
          <div className="px-3 space-y-0.5">
            {PYQ_PAPERS.map((paper) => (
              <div
                key={paper.label}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs
                           text-[#7a7a7a] hover:text-[#c0c0c0] hover:bg-[#1f1f1f] transition-all cursor-pointer"
              >
                <FileText size={11} className="text-[#4a4a4a] shrink-0" />
                <span className="truncate flex-1">{paper.label}</span>
                {paper.verified && (
                  <span className="shrink-0 text-[9px] text-amber-400 border border-amber-400/30 rounded px-1">
                    verified
                  </span>
                )}
              </div>
            ))}
          </div>
        </Section>

        <div className="border-t border-[#1a1a1a] my-1" />

        {/* Class Notes Library */}
        <Section title="Class Notes" icon={<BookOpen size={10} />} defaultOpen>
          <div className="px-3 space-y-0.5">
            {documents.length === 0 ? (
              <div className="px-3 py-3 text-xs text-[#4a4a4a] text-center">
                No notes uploaded yet
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.doc_id}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs
                             text-[#7a7a7a] hover:bg-[#1f1f1f] transition-all"
                >
                  {getFileIcon(doc.filename, 11)}
                  <span className="truncate flex-1">{doc.filename}</span>
                  <div className="shrink-0 flex items-center">
                    <StatusBadge status={doc.status} />
                  </div>
                </div>
              ))
            )}
          </div>
        </Section>
      </div>

      {/* Upload button */}
      <div className="shrink-0 p-4 border-t border-[#1a1a1a]">
        <button
          onClick={onUploadClick}
          disabled={!settings.apiKey}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
                     bg-[#3D46E8] hover:bg-[#5D68FF] disabled:bg-[#1f1f2e] disabled:text-[#3a3a5a]
                     text-white text-sm font-medium transition-colors"
        >
          <Upload size={14} />
          Upload Notes
        </button>
      </div>
    </aside>
  )
}
