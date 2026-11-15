// @vitest-environment jsdom
/**
 * RAG chat UX regression tests (Parts 2–3 of the chat fixes).
 *
 * Contract: the composer is usable the moment /assistant opens; the first
 * submitted message creates the conversation through the existing POST
 * /conversations flow and then sends it through POST …/messages; the new
 * conversation shows up in the history; a failed send never loses the typed
 * text and a retry continues in the same conversation; double submissions
 * create nothing twice; /conversations/:id deep-links into one conversation.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { AssistantPage } from '../features/assistant/AssistantPage'
import type { Message } from '../api/conversations'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function userMessage(id: number, content: string): Message {
  return {
    id,
    conversation: 1,
    role: 'USER',
    content,
    retrieval_mode: '',
    insufficient_evidence: false,
    latency_ms: null,
    created_at: '',
    sources: [],
  }
}

function assistantMessage(id: number, content: string): Message {
  return { ...userMessage(id, content), role: 'ASSISTANT', latency_ms: 120 }
}

const calls: Array<{ method: string; path: string }> = []
let messageStatus = 201
/** Server-side conversation store — the create endpoint really persists. */
let serverConversations: Array<{ id: number; title: string; created_at: string; updated_at: string; archived_at: null }> = []

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost').pathname.replace(/\/+$/, '') || '/'
  const method = init?.method ?? 'GET'
  calls.push({ method, path: url })

  if (url === '/api/v1/auth/refresh') {
    return json({ access: 'token', refresh: 'r', user: { id: 1, email: 's@x.com', role: 'STUDENT' } })
  }
  if (url === '/api/v1/auth/me') {
    return json({ id: 1, email: 's@x.com', role: 'STUDENT', first_name: 'س', last_name: 'د', is_active: true })
  }
  if (url === '/api/v1/conversations') {
    if (method === 'POST') {
      const created = { id: serverConversations.length ? Math.max(...serverConversations.map((c) => c.id)) + 1 : 7, title: '', created_at: '', updated_at: '', archived_at: null }
      serverConversations = [created, ...serverConversations]
      return json(created, 201)
    }
    return json({ results: serverConversations })
  }
  const messageMatch = url.match(/^\/api\/v1\/conversations\/(\d+)\/messages$/)
  if (messageMatch && method === 'POST') {
    if (messageStatus >= 400) return json({ error: { code: 'INTERNAL_ERROR', message: '', details: {} } }, messageStatus)
    return json(
      {
        message: assistantMessage(2, 'پاسخ تست'),
        sources: [],
        user_message: userMessage(1, 'سلام'),
      },
      201,
    )
  }
  const detailMatch = url.match(/^\/api\/v1\/conversations\/(\d+)$/)
  if (detailMatch) {
    return json({
      id: Number(detailMatch[1]),
      title: 'سلام',
      created_at: '',
      updated_at: '',
      archived_at: null,
      messages: [userMessage(1, 'سلام'), assistantMessage(2, 'پاسخ تست')],
    })
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

function renderAssistant(initial = '/assistant') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <AuthProvider>
        <Routes>
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/conversations/:id" element={<AssistantPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

const composer = () => screen.getByPlaceholderText('سوال خود را بنویسید…') as HTMLTextAreaElement

beforeEach(() => {
  calls.length = 0
  messageStatus = 201
  serverConversations = []
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) =>
    Promise.resolve(respond(input, init)),
  ))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('assistant — initial experience', () => {
  it('offers the composer immediately, without clicking گفتگوی جدید', async () => {
    renderAssistant()
    const textarea = (await screen.findByPlaceholderText('سوال خود را بنویسید…')) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.disabled).toBe(false))
    expect(
      calls.filter((call) => call.path === '/api/v1/conversations' && call.method === 'POST'),
    ).toHaveLength(0)
  })

  it('creates the conversation and delivers the first message on submit', async () => {
    renderAssistant()
    const textarea = (await screen.findByPlaceholderText('سوال خود را بنویسید…')) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.disabled).toBe(false))
    fireEvent.change(textarea, { target: { value: 'سلام' } })
    fireEvent.submit(textarea.closest('form')!)

    await screen.findByText('پاسخ تست')
    // Existing flow only: one create, one message send, nothing else.
    expect(calls.filter((call) => call.path === '/api/v1/conversations' && call.method === 'POST')).toHaveLength(1)
    expect(calls.some((call) => call.path === '/api/v1/conversations/7/messages')).toBe(true)
  })

  it('shows the auto-created conversation in the history right away', async () => {
    renderAssistant()
    const textarea = (await screen.findByPlaceholderText('سوال خود را بنویسید…')) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.disabled).toBe(false))
    fireEvent.change(textarea, { target: { value: 'سلام' } })
    fireEvent.submit(textarea.closest('form')!)

    const history = await screen.findByRole('list')
    await waitFor(() => expect(history.textContent).toContain('گفتگوی جدید'))
  })

  it('keeps later messages in the same conversation without a second create', async () => {
    renderAssistant()
    const textarea = (await screen.findByPlaceholderText('سوال خود را بنویسید…')) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.disabled).toBe(false))
    fireEvent.change(textarea, { target: { value: 'سلام' } })
    fireEvent.submit(textarea.closest('form')!)
    await screen.findByText('پاسخ تست')

    fireEvent.change(textarea, { target: { value: 'سوال دوم' } })
    fireEvent.submit(textarea.closest('form')!)
    await waitFor(() =>
      expect(calls.filter((call) => call.path === '/api/v1/conversations/7/messages')).toHaveLength(2),
    )
    expect(calls.filter((call) => call.path === '/api/v1/conversations' && call.method === 'POST')).toHaveLength(1)
  })

  it('ignores a double submit — no duplicate conversation or message', async () => {
    renderAssistant()
    const textarea = (await screen.findByPlaceholderText('سوال خود را بنویسید…')) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.disabled).toBe(false))
    fireEvent.change(textarea, { target: { value: 'سلام' } })
    const form = textarea.closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)

    await screen.findByText('پاسخ تست')
    expect(calls.filter((call) => call.path === '/api/v1/conversations' && call.method === 'POST')).toHaveLength(1)
    expect(calls.filter((call) => call.path === '/api/v1/conversations/7/messages')).toHaveLength(1)
  })

  it('restores the typed message and shows an error when sending fails, then retries in the same conversation', async () => {
    messageStatus = 500
    renderAssistant()
    const textarea = (await screen.findByPlaceholderText('سوال خود را بنویسید…')) as HTMLTextAreaElement
    await waitFor(() => expect(textarea.disabled).toBe(false))
    fireEvent.change(textarea, { target: { value: 'سلام' } })
    fireEvent.submit(textarea.closest('form')!)

    const alert = await screen.findByText('خطا در ارسال پیام. لطفاً دوباره تلاش کنید.')
    await waitFor(() => expect(textarea.value).toBe('سلام'))
    expect(alert).toBeTruthy()
    expect(screen.queryByText('پاسخ تست')).toBeNull()
    // Creation succeeded before the send failed, so the history keeps it.
    expect(
      calls.some((call) => call.path === '/api/v1/conversations' && call.method === 'POST'),
    ).toBe(true)

    // Retry: same conversation, no second create.
    messageStatus = 201
    fireEvent.submit(textarea.closest('form')!)
    await screen.findByText('پاسخ تست')
    expect(calls.filter((call) => call.path === '/api/v1/conversations' && call.method === 'POST')).toHaveLength(1)
    expect(calls.filter((call) => call.path === '/api/v1/conversations/7/messages')).toHaveLength(2)
  })

  it('گفتگوی جدید resets the surface without creating anything', async () => {
    renderAssistant()
    const newChat = await screen.findByRole('button', { name: 'گفتگوی جدید' })
    await waitFor(() => expect(composer().disabled).toBe(false))
    fireEvent.click(newChat)

    expect(composer().disabled).toBe(false)
    expect(composer().value).toBe('')
    expect(
      calls.filter((call) => call.path === '/api/v1/conversations' && call.method === 'POST'),
    ).toHaveLength(0)
  })

  it('loads one conversation directly from /conversations/:id', async () => {
    renderAssistant('/conversations/5')
    await screen.findByText('پاسخ تست')
    expect(screen.getByText('سلام')).toBeTruthy()
    expect(
      calls.some((call) => call.path === '/api/v1/conversations/5' && call.method === 'GET'),
    ).toBe(true)
  })
})
