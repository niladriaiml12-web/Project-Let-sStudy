import client from './client'
import type { QueryResponse, GradeResponse } from '@/types'

export interface QueryRequest {
  question: string
  subject: string
  top_k?: number
}

export interface GradeRequest {
  question: string
  student_answer: string
  subject: string
  max_marks?: number
}

export const askQuestion = (body: QueryRequest): Promise<QueryResponse> =>
  client.post<QueryResponse>('/query/ask', body).then((r) => r.data)

export const gradeAnswer = (body: GradeRequest): Promise<GradeResponse> =>
  client.post<GradeResponse>('/grade/answer', body).then((r) => r.data)
