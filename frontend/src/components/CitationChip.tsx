import type { SourceChunk } from '@/types'
import { FileText, Image } from 'lucide-react'
import { useState } from 'react'

interface CitationChipProps {
  source: SourceChunk
}

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (['jpg', 'jpeg', 'png', 'webp'].includes(ext || '')) {
    return <Image size={11} />
  }
  return <FileText size={11} />
}

export default function CitationChip({ source }: CitationChipProps) {
  const [showPreview, setShowPreview] = useState(false)
  const score = Math.round(source.relevance_score * 100)

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setShowPreview(!showPreview)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs
                   bg-[#1a1a2e] border border-[#3D46E8]/30 text-[#B18CFF]
                   hover:border-[#3D46E8]/60 hover:bg-[#1f1f35] transition-all
                   font-medium cursor-pointer select-none"
      >
        {getFileIcon(source.source_file)}
        <span className="max-w-[140px] truncate">{source.source_file}</span>
        <span className="text-[#5a5a7a] text-[10px]">{score}%</span>
      </button>

      {showPreview && (
        <div className="absolute bottom-full left-0 mb-2 z-50 w-72 p-3
                        bg-[#171717] border border-[#2a2a2a] rounded-lg shadow-xl
                        text-xs text-[#a0a0a0]">
          <div className="font-medium text-[#f0f0f0] mb-1 truncate">
            {source.source_file}
          </div>
          <div className="text-[#5a5a5a] mb-2 text-[10px]">
            Chunk {source.chunk_index} &bull; Relevance {score}%
          </div>
          <div className="text-[#c0c0c0] leading-relaxed line-clamp-4">
            {source.content_preview}
          </div>
          <button
            onClick={() => setShowPreview(false)}
            className="absolute top-2 right-2 text-[#5a5a5a] hover:text-[#a0a0a0]"
          >
            x
          </button>
        </div>
      )}
    </div>
  )
}
