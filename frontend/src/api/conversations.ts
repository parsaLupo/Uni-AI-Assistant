import { authedJson } from '../features/auth/api'

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface MessageSource {
  id: number
  document_id: number
  source_label: string
  page: number
  section: string
  relevance_score: number
  citation_text: string
  created_at: string
}

export interface Message {
  id: number
  conversation: number
  role: 'USER' | 'ASSISTANT' | 'SYSTEM'
  content: string
  retrieval_mode: string
  insufficient_evidence: boolean
  latency_ms: number | null
  created_at: string
  sources: MessageSource[]
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface SendMessageResult {
  message: Message
  sources: Array<Record<string, unknown>>
  user_message: Message
}

export async function listConversations(): Promise<Conversation[]> {
  const data = await authedJson<{ results: Conversation[] } | Conversation[]>('/conversations')
  if (Array.isArray(data)) return data
  return data.results ?? []
}

export async function createConversation(title = ''): Promise<Conversation> {
  return authedJson<Conversation>('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export async function getConversation(id: number): Promise<ConversationDetail> {
  return authedJson<ConversationDetail>(`/conversations/${id}`)
}

export async function renameConversation(id: number, title: string): Promise<Conversation> {
  return authedJson<Conversation>(`/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

export async function deleteConversation(id: number): Promise<void> {
  await authedJson<void>(`/conversations/${id}`, { method: 'DELETE' })
}

export async function sendMessage(id: number, content: string): Promise<SendMessageResult> {
  return authedJson<SendMessageResult>(`/conversations/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}

