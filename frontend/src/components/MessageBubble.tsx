import type { ChatMessage, SourceChunk } from '@/types'
import { Sparkles } from 'lucide-react'
import MarkdownRenderer from './MarkdownRenderer'
import CitationChip from './CitationChip'
import EvaluationCard from './EvaluationCard'

// ---------------------------------------------------------------------------
// Typing indicator
// ---------------------------------------------------------------------------
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-2">
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-[#B18CFF]" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-[#B18CFF]" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-[#B18CFF]" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// User bubble
// ---------------------------------------------------------------------------
function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end animate-slide-up">
      <div className="max-w-[75%]">
        <div className="px-4 py-3 rounded-2xl rounded-tr-sm
                        bg-[#1a1a2e] border border-[#3D46E8]/25
                        text-sm text-[#f0f0f0] leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
        <div className="text-right mt-1 text-[10px] text-[#5a5a5a]">
          {message.mode === 'grade' && (
            <span className="mr-2 text-[#B18CFF]/60">grading request</span>
          )}
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Assistant bubble
// ---------------------------------------------------------------------------
function AssistantBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex gap-3 animate-slide-up">
      {/* Avatar */}
      <div className="shrink-0 w-7 h-7 mt-1 rounded-full
                      bg-gradient-to-br from-[#3D46E8] to-[#B18CFF]
                      flex items-center justify-center">
        <Sparkles size={13} className="text-white" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-semibold text-[#B18CFF] mb-1.5 uppercase tracking-wider">
          Study Engine
        </div>

        {message.isLoading ? (
          <TypingIndicator />
        ) : message.error ? (
          <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3">
            {message.error}
          </div>
        ) : (
          <>
            <div className="text-sm">
              <MarkdownRenderer content={message.content} />
            </div>

            {/* Evaluation card (grading results) */}
            {message.gradeResult && (
              <EvaluationCard grade={message.gradeResult} />
            )}

            {/* Citation chips */}
            {message.sources && message.sources.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {message.sources.map((src: SourceChunk) => (
                  <CitationChip key={`${src.doc_id}-${src.chunk_index}`} source={src} />
                ))}
              </div>
            )}

            {/* No context warning */}
            {message.sources !== undefined && message.sources.length === 0 && (
              <div className="mt-2 text-[11px] text-amber-400/70 flex items-center gap-1.5">
                <span>No indexed notes found for this subject. Upload study materials first.</span>
              </div>
            )}
          </>
        )}

        <div className="mt-1.5 text-[10px] text-[#5a5a5a]">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------
interface MessageBubbleProps {
  message: ChatMessage
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === 'user') return <UserBubble message={message} />
  return <AssistantBubble message={message} />
}
