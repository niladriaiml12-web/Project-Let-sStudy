// Shared TypeScript interfaces for the Study RAG Platform

// ---------------------------------------------------------------------------
// API response types (mirrored from backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface SourceChunk {
  doc_id: string
  source_file: string
  chunk_index: number
  content_preview: string
  relevance_score: number
}

export interface QueryResponse {
  question: string
  answer: string
  sources: SourceChunk[]
  branch: string
  subject: string
  chunks_retrieved: number
  context_found: boolean
}

export interface MissedPoint {
  point: string
  importance: 'critical' | 'important' | 'bonus'
}

export interface GradeResponse {
  question: string
  score: number
  max_score: number
  percentage: number
  grade_letter: string
  feedback: string
  missed_points: MissedPoint[]
  correct_points: string[]
  context_based: boolean
  subject: string
  branch: string
}

export interface DocumentStatusResponse {
  doc_id: string
  original_filename: string
  doc_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  chunk_count: number | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface IngestResponse {
  doc_id: string
  filename: string
  subject: string
  branch: string
  status: string
  message: string
}

export interface Group {
  id: number
  name: string
  branch_code: string
  description: string | null
}

export interface Subject {
  id: number
  group_id: number
  name: string
  subject_code: string
  description: string | null
}

// ---------------------------------------------------------------------------
// Local UI state types
// ---------------------------------------------------------------------------

export type MessageRole = 'user' | 'assistant'
export type MessageMode = 'query' | 'grade'

export interface ChatMessage {
  id: string
  role: MessageRole
  mode: MessageMode
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  gradeResult?: GradeResponse
  isLoading?: boolean
  error?: string
}

export interface DocumentEntry {
  doc_id: string
  filename: string
  subject_code: string
  status: DocumentStatusResponse['status']
  chunk_count?: number
  doc_type: string
  uploadedAt: Date
}

export interface AppSettings {
  apiKey: string
  activeSubject: string
  groupName: string
  branchCode: string
}
