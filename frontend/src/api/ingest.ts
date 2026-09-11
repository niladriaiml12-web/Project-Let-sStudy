import client from './client'
import type { IngestResponse, DocumentStatusResponse } from '@/types'

export const uploadDocument = (
  file: File,
  subjectCode: string,
  docType: string = 'class_notes',
): Promise<IngestResponse> => {
  const form = new FormData()
  form.append('file', file)
  form.append('subject_code', subjectCode)
  form.append('doc_type', docType)
  return client.post<IngestResponse>('/ingest/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const getDocumentStatus = (docId: string): Promise<DocumentStatusResponse> =>
  client.get<DocumentStatusResponse>(`/ingest/status/${docId}`).then((r) => r.data)

export const deleteDocument = (docId: string) =>
  client.delete(`/ingest/${docId}`).then((r) => r.data)
