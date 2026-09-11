import client from './client'
import type { Group, Subject } from '@/types'

export const getGroups = (): Promise<Group[]> =>
  client.get<Group[]>('/groups').then((r) => r.data)

export const getSubjects = (groupId: number): Promise<Subject[]> =>
  client.get<Subject[]>(`/groups/${groupId}/subjects`).then((r) => r.data)

export const checkHealth = (): Promise<{ status: string }> =>
  client.get('/health').then((r) => r.data)
