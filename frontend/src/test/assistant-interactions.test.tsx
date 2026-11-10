// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { AssistantPage } from '../features/assistant/AssistantPage'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/auth/refresh')) return Promise.resolve(json({ access: 'token', user: { id: 1, email: 's@x.com', role: 'STUDENT' } }))
    if (url.includes('/auth/me')) return Promise.resolve(json({ id: 1, email: 's@x.com', role: 'STUDENT', first_name: '', last_name: '', is_active: true }))
    if (url.includes('/messages')) return Promise.resolve(json({ message: { id: 2, conversation: 1, role: 'ASSISTANT', content: 'پاسخ تست', retrieval_mode: 'RAG', insufficient_evidence: false, created_at: '', sources: [] }, sources: [], user_message: { id: 1, conversation: 1, role: 'USER', content: 'سلام', retrieval_mode: '', insufficient_evidence: false, created_at: '', sources: [] } }, 201))
    if (url.endsWith('/conversations/') || url.endsWith('/conversations')) return Promise.resolve(json({ count: 0, next: null, previous: null, results: [] }))
    if (url.includes('/conversations/')) return Promise.resolve(json({ id: 1, title: 'جدید', created_at: '', updated_at: '', archived_at: null, messages: [] }))
    return Promise.resolve(json({ id: 1, title: '' }, 201))
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('assistant interactions', () => {
  it('creates conversation, types, sends, and renders response', async () => {
    const qc = new QueryClient()
    render(
      <MemoryRouter>
        <QueryClientProvider client={qc}>
          <AuthProvider>
            <AssistantPage />
          </AuthProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    )
    const newBtn = await screen.findByRole('button', { name: 'گفتگوی جدید' })
    fireEvent.click(newBtn)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const textarea = await screen.findByPlaceholderText('سوال خود را بنویسید…')
    fireEvent.change(textarea, { target: { value: 'سلام' } })
    const sendBtn = screen.getByRole('button', { name: 'ارسال' })
    expect((sendBtn as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(sendBtn)
    await screen.findByText('پاسخ تست')
  })
})
