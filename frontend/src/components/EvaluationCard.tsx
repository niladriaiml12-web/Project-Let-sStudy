import type { GradeResponse, MissedPoint } from '@/types'
import { TrendingUp, AlertCircle, CheckCircle2, BookOpen } from 'lucide-react'

interface EvaluationCardProps {
  grade: GradeResponse
}

function ScoreBar({ percentage }: { percentage: number }) {
  const color =
    percentage >= 80 ? '#4ade80' :
    percentage >= 60 ? '#facc15' :
    percentage >= 40 ? '#fb923c' : '#f87171'

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-[#2a2a2a] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-mono text-[#a0a0a0]">{percentage}%</span>
    </div>
  )
}

function GradeBadge({ letter }: { letter: string }) {
  const colors: Record<string, string> = {
    'A+': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    'A':  'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    'B':  'bg-blue-500/20 text-blue-400 border-blue-500/30',
    'C':  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    'D':  'bg-orange-500/20 text-orange-400 border-orange-500/30',
    'F':  'bg-red-500/20 text-red-400 border-red-500/30',
  }
  const cls = colors[letter] || 'bg-[#2a2a2a] text-[#a0a0a0] border-[#3a3a3a]'
  return (
    <span className={`inline-flex items-center justify-center w-9 h-9 rounded-lg border text-base font-bold ${cls}`}>
      {letter}
    </span>
  )
}

export default function EvaluationCard({ grade }: EvaluationCardProps) {
  return (
    <div className="mt-3 rounded-xl border border-[#2a2a2a] bg-[#111118] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a2a] bg-[#0f0f18]">
        <div className="flex items-center gap-2">
          <TrendingUp size={14} className="text-[#B18CFF]" />
          <span className="text-xs font-semibold uppercase tracking-widest text-[#a0a0a0]">
            Evaluation
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!grade.context_based && (
            <span className="text-[10px] text-amber-400 border border-amber-400/30 rounded px-1.5 py-0.5">
              No reference material
            </span>
          )}
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Score row */}
        <div className="flex items-center gap-4">
          <GradeBadge letter={grade.grade_letter} />
          <div className="flex-1">
            <div className="flex items-baseline gap-1.5 mb-1.5">
              <span className="text-2xl font-bold text-white">{grade.score}</span>
              <span className="text-sm text-[#5a5a5a]">/ {grade.max_score}</span>
            </div>
            <ScoreBar percentage={grade.percentage} />
          </div>
        </div>

        {/* Feedback */}
        <div className="text-sm text-[#c0c0c0] leading-relaxed bg-[#161620] rounded-lg p-3 border border-[#2a2a2a]">
          {grade.feedback}
        </div>

        {/* Correct points */}
        {grade.correct_points.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-emerald-400">
              <CheckCircle2 size={12} />
              Covered ({grade.correct_points.length})
            </div>
            <ul className="space-y-1">
              {grade.correct_points.map((pt: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-xs text-[#a0a0a0]">
                  <span className="text-emerald-500 mt-0.5 shrink-0">+</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Missed points */}
        {grade.missed_points.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-red-400">
              <AlertCircle size={12} />
              Missing ({grade.missed_points.length})
            </div>
            <ul className="space-y-1">
              {grade.missed_points.map((pt: MissedPoint, i: number) => (
                <li key={i} className="flex items-start gap-2 text-xs text-[#a0a0a0]">
                  <span
                    className={`shrink-0 mt-0.5 font-bold ${
                      pt.importance === 'critical' ? 'text-red-400' :
                      pt.importance === 'important' ? 'text-orange-400' : 'text-yellow-400'
                    }`}
                  >
                    {pt.importance === 'critical' ? '!!' : pt.importance === 'important' ? '!' : '+'}
                  </span>
                  <span>{pt.point}</span>
                  {pt.importance === 'critical' && (
                    <span className="ml-auto shrink-0 text-[10px] text-red-400 border border-red-400/30 rounded px-1">
                      critical
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Subject info */}
        <div className="flex items-center gap-1.5 pt-1 text-[10px] text-[#5a5a5a]">
          <BookOpen size={10} />
          <span>{grade.branch} &bull; {grade.subject}</span>
        </div>
      </div>
    </div>
  )
}
