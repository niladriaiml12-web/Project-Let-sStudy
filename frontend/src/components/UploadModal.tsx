import { useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { X, Upload, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { uploadDocument, getDocumentStatus } from '@/api/ingest'
import type { AppSettings, DocumentEntry } from '@/types'

type UploadStep = 'idle' | 'uploading' | 'ocr' | 'vectorizing' | 'done' | 'error'

interface UploadState {
  step: UploadStep
  filename: string
  docId?: string
  error?: string
  chunks?: number
}

const STEP_LABELS: Record<UploadStep, string> = {
  idle: 'Ready',
  uploading: 'Uploading to server...',
  ocr: 'Gemini Vision OCR running...',
  vectorizing: 'Vectorizing into Community Store...',
  done: 'Indexed successfully',
  error: 'Failed',
}

function StepTracker({ step }: { step: UploadStep }) {
  const steps: UploadStep[] = ['uploading', 'ocr', 'vectorizing', 'done']
  const stepIndex = steps.indexOf(step)

  return (
    <div className="flex items-center gap-1 mt-4">
      {steps.map((s, i) => {
        const done = stepIndex > i
        const active = stepIndex === i
        const isLast = i === steps.length - 1
        return (
          <div key={s} className="flex items-center flex-1">
            <div className="flex flex-col items-center gap-1.5 flex-1">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all
                ${done ? 'bg-emerald-500 text-white' :
                  active ? 'bg-[#3D46E8] text-white' :
                  'bg-[#2a2a2a] text-[#5a5a5a]'}`}>
                {done ? <CheckCircle2 size={12} /> : active ? <Loader2 size={12} className="animate-spin" /> : i + 1}
              </div>
              <span className={`text-[10px] text-center leading-tight ${active ? 'text-[#B18CFF]' : done ? 'text-emerald-400' : 'text-[#5a5a5a]'}`}>
                {s === 'uploading' ? 'Upload' : s === 'ocr' ? 'OCR' : s === 'vectorizing' ? 'Vectorize' : 'Done'}
              </span>
            </div>
            {!isLast && (
              <div className={`flex-1 h-px mx-1 transition-all ${done || (active && i < stepIndex) ? 'bg-emerald-500' : 'bg-[#2a2a2a]'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

interface UploadModalProps {
  open: boolean
  onClose: () => void
  settings: AppSettings
  subjects: string[]
  onDocumentAdded: (doc: DocumentEntry) => void
}

export default function UploadModal({ open, onClose, settings, subjects, onDocumentAdded }: UploadModalProps) {
  const [selectedSubject, setSelectedSubject] = useState(settings.activeSubject || '')
  const [docType, setDocType] = useState('class_notes')
  const [uploadState, setUploadState] = useState<UploadState>({ step: 'idle', filename: '' })
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const startPolling = (docId: string, filename: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const status = await getDocumentStatus(docId)
        if (status.status === 'processing') {
          setUploadState((s) => ({ ...s, step: 'vectorizing' }))
        } else if (status.status === 'completed') {
          stopPolling()
          setUploadState({ step: 'done', filename, docId, chunks: status.chunk_count ?? 0 })
          onDocumentAdded({
            doc_id: docId,
            filename,
            subject_code: selectedSubject,
            status: 'completed',
            chunk_count: status.chunk_count ?? 0,
            doc_type: docType,
            uploadedAt: new Date(),
          })
        } else if (status.status === 'failed') {
          stopPolling()
          setUploadState({ step: 'error', filename, error: status.error_message || 'Processing failed' })
        }
      } catch {
        // ignore polling errors
      }
    }, 2000)
  }

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0]
    if (!file || !selectedSubject) return

    setUploadState({ step: 'uploading', filename: file.name })

    try {
      const res = await uploadDocument(file, selectedSubject, docType)
      setUploadState({ step: 'ocr', filename: file.name, docId: res.doc_id })
      startPolling(res.doc_id, file.name)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setUploadState({ step: 'error', filename: file.name, error: msg })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSubject, docType])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'], 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploadState.step !== 'idle' && uploadState.step !== 'done' && uploadState.step !== 'error',
  })

  const reset = () => { stopPolling(); setUploadState({ step: 'idle', filename: '' }) }
  const handleClose = () => { reset(); onClose() }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-[#111] border border-[#2a2a2a] rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#2a2a2a]">
          <div>
            <h2 className="text-sm font-semibold text-white">Upload Study Material</h2>
            <p className="text-xs text-[#5a5a5a] mt-0.5">{settings.groupName} &bull; {settings.branchCode}</p>
          </div>
          <button onClick={handleClose} className="text-[#5a5a5a] hover:text-white transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Subject selector */}
          <div>
            <label className="text-xs font-medium text-[#a0a0a0] mb-1.5 block">Subject</label>
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="w-full bg-[#171717] border border-[#2a2a2a] rounded-lg px-3 py-2
                         text-sm text-[#f0f0f0] focus:outline-none focus:border-[#3D46E8]/50"
            >
              <option value="">Select subject...</option>
              {subjects.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {/* Doc type */}
          <div>
            <label className="text-xs font-medium text-[#a0a0a0] mb-1.5 block">Document Type</label>
            <div className="flex gap-2">
              {[
                { value: 'class_notes', label: 'Class Notes' },
                { value: 'pyq', label: 'PYQ' },
                { value: 'reference', label: 'Reference' },
              ].map((t) => (
                <button
                  key={t.value}
                  onClick={() => setDocType(t.value)}
                  className={`flex-1 py-1.5 text-xs rounded-lg border transition-all ${
                    docType === t.value
                      ? 'bg-[#3D46E8]/20 border-[#3D46E8]/50 text-[#B18CFF]'
                      : 'bg-transparent border-[#2a2a2a] text-[#5a5a5a] hover:border-[#3a3a3a]'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all
              ${isDragActive
                ? 'border-[#3D46E8] bg-[#3D46E8]/10'
                : 'border-[#2a2a2a] bg-[#171717] hover:border-[#3a3a3a]'}
              ${(uploadState.step !== 'idle' && uploadState.step !== 'done' && uploadState.step !== 'error')
                ? 'pointer-events-none opacity-60' : ''}`}
          >
            <input {...getInputProps()} />
            {uploadState.step === 'idle' || uploadState.step === 'done' || uploadState.step === 'error' ? (
              <>
                <Upload size={24} className="mx-auto mb-3 text-[#5a5a5a]" />
                <p className="text-sm text-[#a0a0a0]">
                  {isDragActive ? 'Drop it here' : 'Drag & drop or click to upload'}
                </p>
                <p className="text-xs text-[#5a5a5a] mt-1">PDF, JPG, PNG, WebP &bull; max 50MB</p>
              </>
            ) : (
              <div className="py-2">
                <Loader2 size={24} className="mx-auto mb-3 text-[#3D46E8] animate-spin" />
                <p className="text-sm text-[#a0a0a0]">{STEP_LABELS[uploadState.step]}</p>
                {uploadState.filename && (
                  <p className="text-xs text-[#5a5a5a] mt-1 truncate">{uploadState.filename}</p>
                )}
              </div>
            )}
          </div>

          {/* Step tracker */}
          {uploadState.step !== 'idle' && (
            <StepTracker step={uploadState.step} />
          )}

          {/* Status messages */}
          {uploadState.step === 'done' && (
            <div className="flex items-center gap-2 text-sm text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 rounded-lg px-4 py-3">
              <CheckCircle2 size={16} />
              <span>
                Indexed {uploadState.chunks} chunks &bull; {uploadState.filename}
              </span>
              <button onClick={reset} className="ml-auto text-xs underline">Upload another</button>
            </div>
          )}

          {uploadState.step === 'error' && (
            <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3">
              <AlertCircle size={16} />
              <span className="flex-1">{uploadState.error}</span>
              <button onClick={reset} className="ml-auto text-xs underline">Try again</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
