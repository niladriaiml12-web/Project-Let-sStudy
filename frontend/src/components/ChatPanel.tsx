import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import { Send, GraduationCap, MessageSquare, Settings } from 'lucide-react'
import MessageBubble from './MessageBubble'
import type { ChatMessage, AppSettings } from '@/types'
import { askQuestion, gradeAnswer } from '@/api/query'

// ---------------------------------------------------------------------------
// Auto-detect grading intent
// Grading heuristics: starts with "grade", "evaluate", "check my",
// "my answer is", "mark this", or text longer than 300 chars with no "?"
// ---------------------------------------------------------------------------
function detectMode(text: string): 'grade' | 'query' {
  const t = text.trim().toLowerCase()
  if (t.startsWith('grade') || t.startsWith('evaluate') || t.startsWith('check my') ||
      t.startsWith('mark this') || t.includes('my answer') || t.includes('my response')) {
    return 'grade'
  }
  if (text.trim().length > 300 && !text.includes('?')) return 'grade'
  return 'query'
}

// Extract the question from a grading message
// e.g. "Grade this: Q: What is DP? A: DP is..."
function extractGradingParts(text: string): { question: string; answer: string } {
  const qMatch = text.match(/[Qq]uestion[:\s]+(.+?)(?:[Aa]nswer[:\s]|[Aa]:|$)/s)
  const aMatch = text.match(/[Aa]nswer[:\s]+(.+)$/s) || text.match(/[Aa]:\s*(.+)$/s)
  if (qMatch && aMatch) {
    return { question: qMatch[1].trim(), answer: aMatch[1].trim() }
  }
  // Fallback: treat entire text as answer, use last user question as the question
  return { question: '', answer: text.trim() }
}

function uuid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------
function EmptyState({ subject }: { subject: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-8 py-16 select-none">
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#3D46E8]/20 to-[#B18CFF]/20
                      border border-[#3D46E8]/20 flex items-center justify-center mb-5">
        <GraduationCap size={24} className="text-[#B18CFF]" />
      </div>
      <h2 className="text-base font-semibold text-white mb-2">
        {subject ? `Ask about ${subject}` : 'Select a subject to begin'}
      </h2>
      <p className="text-sm text-[#5a5a5a] max-w-xs leading-relaxed">
        Ask any question from your notes, or paste your answer to get it graded against your study materials.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-xs text-left">
        {[
          'Explain dynamic programming with an example',
          'What is a support vector machine?',
          'Grade my answer: [paste your answer here]',
        ].map((hint) => (
          <div key={hint}
               className="px-3 py-2.5 rounded-lg border border-[#2a2a2a] bg-[#171717]/60
                          text-xs text-[#7a7a7a] leading-relaxed">
            {hint}
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Chat input
// ---------------------------------------------------------------------------
interface InputBarProps {
  onSend: (text: string) => void
  disabled: boolean
  subject: string
}

function InputBar({ onSend, disabled, subject }: InputBarProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim()) { onSend(value); setValue('') }
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [value])

  const mode = detectMode(value)

  return (
    <div className="border-t border-[#1f1f1f] bg-[#0d0d0d]/80 backdrop-blur-sm p-4">
      <div className="relative flex items-end gap-3 bg-[#171717] border border-[#2a2a2a]
                      rounded-xl p-3 focus-within:border-[#3D46E8]/50 transition-colors">
        {/* Mode indicator */}
        <div className="shrink-0 mb-0.5">
          {mode === 'grade' ? (
            <GraduationCap size={16} className="text-[#B18CFF]" />
          ) : (
            <MessageSquare size={16} className="text-[#3D46E8]" />
          )}
        </div>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled || !subject}
          placeholder={
            !subject
              ? 'Select a subject from the sidebar first...'
              : 'Ask a question or paste your answer to grade...'
          }
          rows={1}
          className="flex-1 bg-transparent text-sm text-[#f0f0f0] placeholder-[#4a4a4a]
                     resize-none outline-none leading-relaxed min-h-[24px]
                     disabled:cursor-not-allowed"
          style={{ maxHeight: '160px' }}
        />

        <button
          onClick={() => { if (value.trim()) { onSend(value); setValue('') } }}
          disabled={disabled || !value.trim() || !subject}
          className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
                     bg-[#3D46E8] hover:bg-[#5D68FF] disabled:bg-[#1f1f2e] disabled:text-[#3a3a5a]
                     text-white transition-colors"
        >
          <Send size={13} />
        </button>
      </div>
      <div className="mt-2 flex items-center justify-between text-[10px] text-[#4a4a4a] px-1">
        <span>Enter to send &bull; Shift+Enter for newline</span>
        {value.length > 0 && (
          <span className={mode === 'grade' ? 'text-[#B18CFF]' : 'text-[#3D46E8]'}>
            {mode === 'grade' ? 'Grading mode' : 'Query mode'}
          </span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main ChatPanel
// ---------------------------------------------------------------------------
interface ChatPanelProps {
  settings: AppSettings
  onOpenSettings: () => void
}

export default function ChatPanel({ settings, onOpenSettings }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastUserQuestion = useRef<string>('')

  // Auto-scroll on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addMessage = (msg: ChatMessage) =>
    setMessages((prev) => [...prev, msg])

  const updateLastAssistant = (updater: (m: ChatMessage) => ChatMessage) =>
    setMessages((prev) => {
      const copy = [...prev]
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === 'assistant') { copy[i] = updater(copy[i]); break }
      }
      return copy
    })

  const handleSend = async (text: string) => {
    if (!settings.activeSubject || !settings.apiKey) {
      onOpenSettings()
      return
    }

    const mode = detectMode(text)
    const userMsg: ChatMessage = {
      id: uuid(), role: 'user', mode, content: text, timestamp: new Date(),
    }
    addMessage(userMsg)
    setLoading(true)

    // Placeholder assistant message
    const assistantId = uuid()
    addMessage({ id: assistantId, role: 'assistant', mode, content: '', timestamp: new Date(), isLoading: true })

    try {
      if (mode === 'query') {
        lastUserQuestion.current = text
        const res = await askQuestion({ question: text, subject: settings.activeSubject })
        updateLastAssistant((m) => ({
          ...m,
          content: res.answer,
          sources: res.sources,
          isLoading: false,
        }))
      } else {
        // Grading mode
        const { question, answer } = extractGradingParts(text)
        const resolvedQuestion = question || lastUserQuestion.current || text.slice(0, 200)
        const res = await gradeAnswer({
          question: resolvedQuestion,
          student_answer: answer || text,
          subject: settings.activeSubject,
        })
        updateLastAssistant((m) => ({
          ...m,
          content: res.feedback,
          gradeResult: res,
          isLoading: false,
        }))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Request failed. Check your API key and that the backend is running.'
      updateLastAssistant((m) => ({ ...m, content: '', error: msg, isLoading: false }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-6 py-4
                      border-b border-[#1f1f1f] bg-[#0d0d0d]/60 backdrop-blur-sm">
        <div>
          <div className="text-sm font-semibold text-white">
            {settings.groupName || 'Study Engine'}
          </div>
          <div className="text-xs text-[#5a5a5a] mt-0.5">
            {settings.activeSubject
              ? `Subject: ${settings.activeSubject}`
              : 'No subject selected'}
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="px-2.5 py-1 rounded-full bg-[#171717] border border-[#2a2a2a] text-[11px] text-[#A0A0A0] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>AI: Gemini 3.5 (Backend Connected)</span>
          </div>
          <button
            onClick={onOpenSettings}
            className="text-xs text-[#7a7a7a] hover:text-white p-1.5 rounded-lg border border-[#222] hover:border-[#333] transition-colors"
            title="Department & Subject Settings"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5 min-h-0">
        {messages.length === 0
          ? <EmptyState subject={settings.activeSubject} />
          : messages.map((m) => <MessageBubble key={m.id} message={m} />)
        }
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <InputBar onSend={handleSend} disabled={loading} subject={settings.activeSubject} />
    </div>
  )
}
