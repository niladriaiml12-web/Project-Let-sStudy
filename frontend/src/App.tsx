import { useState, useEffect } from 'react'
import ShaderCanvas from '@/components/ShaderCanvas'
import Sidebar from '@/components/Sidebar'
import ChatPanel from '@/components/ChatPanel'
import UploadModal from '@/components/UploadModal'
import SettingsModal from '@/components/SettingsModal'
import type { AppSettings, DocumentEntry, Group, Subject } from '@/types'
import { getGroups, getSubjects } from '@/api/groups'

// ---------------------------------------------------------------------------
// Load persisted settings from localStorage with smart defaults
// ---------------------------------------------------------------------------
const DEFAULT_API_KEY = 'dev-key-cse-aiml-2026'

function loadSettings(): AppSettings {
  const storedKey = localStorage.getItem('study_api_key')
  const validKey = storedKey && storedKey.startsWith('dev-key-') ? storedKey : DEFAULT_API_KEY
  return {
    apiKey: validKey,
    activeSubject: localStorage.getItem('study_active_subject') || 'ML',
    groupName: localStorage.getItem('study_group_name') || 'CSE AIML 2026',
    branchCode: localStorage.getItem('study_branch_code') || 'CSE_AIML',
  }
}

export default function App() {
  const [settings, setSettings] = useState<AppSettings>(loadSettings)
  const [groups, setGroups] = useState<Group[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [documents, setDocuments] = useState<DocumentEntry[]>([])
  const [uploadOpen, setUploadOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Ensure valid tenant key is saved to localStorage on first launch or reset
  useEffect(() => {
    const key = localStorage.getItem('study_api_key')
    if (!key || !key.startsWith('dev-key-')) {
      localStorage.setItem('study_api_key', DEFAULT_API_KEY)
      localStorage.setItem('study_group_name', 'CSE AIML 2026')
      localStorage.setItem('study_branch_code', 'CSE_AIML')
      localStorage.setItem('study_active_subject', 'ML')
      setSettings((s) => ({
        ...s,
        apiKey: DEFAULT_API_KEY,
        groupName: 'CSE AIML 2026',
        branchCode: 'CSE_AIML',
        activeSubject: 'ML',
      }))
    }
  }, [])

  // Load groups and active group subjects
  useEffect(() => {
    const load = async () => {
      try {
        const fetchedGroups = await getGroups()
        setGroups(fetchedGroups)

        if (fetchedGroups.length > 0) {
          // Find currently selected group or default to the first one
          const currentGroup =
            fetchedGroups.find((g) => g.branch_code === settings.branchCode) ||
            fetchedGroups[0]

          const subs = await getSubjects(currentGroup.id)
          setSubjects(subs)

          const activeSub =
            subs.some((s) => s.subject_code === settings.activeSubject)
              ? settings.activeSubject
              : subs[0]?.subject_code || ''

          const updatedSettings: AppSettings = {
            ...settings,
            groupName: currentGroup.name,
            branchCode: currentGroup.branch_code,
            activeSubject: activeSub,
          }
          localStorage.setItem('study_group_name', currentGroup.name)
          localStorage.setItem('study_branch_code', currentGroup.branch_code)
          localStorage.setItem('study_active_subject', activeSub)
          setSettings(updatedSettings)
        }
      } catch {
        // Backend may be starting or offline
      }
    }

    load()
  }, [settings.branchCode])

  const handleBranchSelect = async (branchCode: string) => {
    const group = groups.find((g) => g.branch_code === branchCode)
    if (!group) return
    const key = branchCode === 'CSE_CORE' ? 'dev-key-cse-core-2026' : 'dev-key-cse-aiml-2026'
    localStorage.setItem('study_api_key', key)
    localStorage.setItem('study_group_name', group.name)
    localStorage.setItem('study_branch_code', group.branch_code)
    try {
      const subs = await getSubjects(group.id)
      setSubjects(subs)
      const defaultSub = subs[0]?.subject_code || ''
      localStorage.setItem('study_active_subject', defaultSub)
      setSettings({
        apiKey: key,
        groupName: group.name,
        branchCode: group.branch_code,
        activeSubject: defaultSub,
      })
    } catch {
      setSettings((prev) => ({
        ...prev,
        apiKey: key,
        groupName: group.name,
        branchCode: group.branch_code,
      }))
    }
  }

  const handleSettingsSave = (newSettings: AppSettings) => {
    setSettings(newSettings)
  }

  const handleSubjectSelect = (code: string) => {
    const updated = { ...settings, activeSubject: code }
    localStorage.setItem('study_active_subject', code)
    setSettings(updated)
  }

  const handleDocumentAdded = (doc: DocumentEntry) => {
    setDocuments((prev) => [doc, ...prev])
  }

  return (
    <div className="relative w-full h-screen overflow-hidden">
      {/* Layer 0: WebGL halftone shader background */}
      <ShaderCanvas />

      {/* Layer 1: Frosted glass overlay — tones down the shader for readability */}
      <div
        className="fixed inset-0 z-[1]"
        style={{ background: 'rgba(8, 8, 12, 0.72)', backdropFilter: 'blur(0px)' }}
      />

      {/* Layer 2: App UI */}
      <div className="relative z-10 flex h-screen overflow-hidden">
        <Sidebar
          settings={settings}
          groups={groups}
          subjects={subjects}
          documents={documents}
          onUploadClick={() => setUploadOpen(true)}
          onSettingsClick={() => setSettingsOpen(true)}
          onSubjectSelect={handleSubjectSelect}
          onBranchSelect={handleBranchSelect}
        />

        <main className="flex-1 min-w-0 flex flex-col h-full">
          <ChatPanel
            settings={settings}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        </main>
      </div>

      {/* Modals */}
      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        settings={settings}
        subjects={subjects.map((s) => s.subject_code)}
        onDocumentAdded={handleDocumentAdded}
      />

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        groups={groups}
        subjects={subjects}
        onSave={handleSettingsSave}
        onBranchSelect={handleBranchSelect}
      />
    </div>
  )
}
