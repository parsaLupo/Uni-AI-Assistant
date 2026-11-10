/**
 * /assistant (+ /conversations/:id) — Smart AssistantDESIGN.md shell.
 *
 * The design's chat surface needs the Phase 10 conversation API
 * (POST /conversations/:id/messages/, docs/api/chat.md), which does not exist
 * yet, so the composer is rendered but disabled with the honest Persian notice
 * (assistantPage.notReady*) rather than a fake reply. History shows the empty
 * state for the same reason. Phase 10 swaps the notice for live messages —
 * layout, RTL and styling stay as-is.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { EmptyState, PageHeader, cardCls } from '../../components/ui'
import { assistantPage } from '../../i18n/fa'
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  renameConversation,
  sendMessage,
  type Conversation,
  type Message,
} from '../../api/conversations'

export function AssistantPage() {
  const { status: authStatus } = useAuth()
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  useEffect(() => {
    if (authStatus === 'anonymous') {
      navigate('/login')
    }
  }, [authStatus, navigate])

  useEffect(() => {
    if (authStatus !== 'authenticated') return
    let cancelled = false
    listConversations()
      .then((items) => {
        if (cancelled) return
        setConversations(items)
        if (items.length > 0) setSelectedId(items[0].id)
      })
      .catch(() => {
        if (!cancelled) setError('??????? ????? ???. ????? ?????? ???? ????.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [authStatus])

  useEffect(() => {
    if (selectedId === null) {
      setMessages([])
      return
    }
    let cancelled = false
    getConversation(selectedId)
      .then((conversation) => {
        if (!cancelled) setMessages(conversation.messages ?? [])
      })
      .catch(() => {
        if (!cancelled) setMessages([])
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  async function handleNewChat() {
    if (authStatus !== 'authenticated') {
      navigate('/login')
      return
    }
    try {
      const conversation = await createConversation()
      setConversations((prev) => [conversation, ...prev])
      setSelectedId(conversation.id)
      setMessages([])
    } catch {
      setError('??????? ????? ???. ????? ?????? ???? ????.')
    }
  }

  async function handleRename(id: number) {
    try {
      const updated = await renameConversation(id, editingTitle.trim() || 'گفتگو')
      setConversations((prev) => prev.map((item) => (item.id === id ? updated : item)))
      setEditingId(null)
    } catch {
      setError('??????? ????? ???. ????? ?????? ???? ????.')
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteConversation(id)
      setConversations((prev) => prev.filter((item) => item.id !== id))
      if (selectedId === id) {
        setSelectedId(null)
        setMessages([])
      }
    } catch {
      setError('??????? ????? ???. ????? ?????? ???? ????.')
    }
  }

  async function handleSend(event: { preventDefault: () => void }) {
    if (authStatus !== 'authenticated') {
      navigate('/login')
      return
    }
    event.preventDefault()
    if (!input.trim() || selectedId === null || sending) return
    const content = input.trim()
    setInput('')
    setSending(true)
    setError(null)
    try {
      const result = await sendMessage(selectedId, content)
      setMessages((prev) => [...prev, result.user_message, result.message])
    } catch {
      setError('??????? ????? ???. ????? ?????? ???? ????.')
    } finally {
      setSending(false)
    }
  }
  async function handleRetry() {
    const lastUser = [...messages].reverse().find((item) => item.role === 'USER')
    if (!lastUser) return
    setInput(lastUser.content)
  }

  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader title={assistantPage.title} subtitle={assistantPage.subtitle} actions={<button type="button" onClick={handleNewChat} className="rounded bg-primary-container px-space-md py-2 text-label-lg font-semibold text-on-primary">{assistantPage.newChat}</button>} />
      <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-[1fr_18rem]">
        <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`} aria-label={assistantPage.title}>
          {loading ? <div className="text-body-sm text-on-surface-variant">{assistantPage.sending}</div> : selectedId === null ? (
            <div className="flex flex-col items-center gap-space-sm rounded-xl bg-surface-container-low px-space-lg py-space-xl text-center">
              <h2 className="m-0 text-headline-md font-bold text-on-surface">{assistantPage.welcomeTitle}</h2>
              <p className="m-0 max-w-lg text-body-sm text-on-surface-variant">{assistantPage.welcomeBody}</p>
            </div>
          ) : (
            <div className="flex flex-col gap-space-md">
              {messages.length === 0 ? <EmptyState message={assistantPage.noHistory} /> : messages.map((message) => (
                <article key={message.id} className={`rounded-xl p-space-md ${message.role === 'USER' ? 'bg-primary-container/10' : message.insufficient_evidence ? 'border border-[#FDE68A] bg-[#FFFBEB]' : 'bg-surface-container-low'}`}>
                  <p className="m-0 whitespace-pre-wrap text-body-sm text-on-surface">{message.content}</p>
                  {message.insufficient_evidence ? <p className="mt-space-xs text-body-sm font-bold text-[#92400E]">شواهد کافی برای پاسخ قطعی یافت نشد.</p> : null}
                  {message.role === 'ASSISTANT' && message.sources?.length ? (
                    <ul className="mt-space-sm flex flex-col gap-space-xs">
                      {message.sources.map((source) => (
                        <li key={source.id} className="text-body-sm text-on-surface-variant">{source.source_label} — صفحه {source.page} — {source.section}</li>
                      ))}
                    </ul>
                  ) : null}
                  {message.role === 'ASSISTANT' ? (
                    <div className="mt-space-sm flex gap-space-sm">
                      <button type="button" onClick={() => navigator.clipboard?.writeText(message.content)} className="text-body-sm">کپی</button>
                      <button type="button" onClick={handleRetry} className="text-body-sm">تلاش دوباره</button>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
          {error ? <div role="status" aria-live="polite" className="rounded-xl border border-[#FDE68A] bg-[#FFFBEB] px-space-md py-space-sm text-body-sm text-[#92400E]">{error}</div> : null}
          <form className="flex items-end gap-space-sm" onSubmit={handleSend}>
            <label htmlFor="assistant-composer" className="sr-only">{assistantPage.composerPlaceholder}</label>
            <textarea id="assistant-composer" dir="auto" rows={2} value={input} onChange={(event) => setInput(event.target.value)} disabled={selectedId === null || sending} placeholder={assistantPage.composerPlaceholder} className={`${cardCls} min-h-[3rem] w-full resize-y px-space-md py-space-sm text-body-sm`} />
            <button type="submit" disabled={selectedId === null || sending || !input.trim()} className="rounded bg-primary-container px-space-lg py-3 text-label-lg font-semibold text-on-primary disabled:opacity-75">{sending ? assistantPage.sending : assistantPage.send}</button>
          </form>
        </section>
        <aside className={`${cardCls} flex flex-col gap-space-sm p-space-md`} aria-label={assistantPage.history}>
          <h3 className="m-0 text-label-lg font-bold text-on-surface">{assistantPage.history}</h3>
          {conversations.length === 0 ? <EmptyState message={assistantPage.noHistory} /> : (
            <ul className="flex flex-col gap-space-xs">
              {conversations.map((conversation) => (
                <li key={conversation.id} className="flex flex-col gap-space-xs">
                  {editingId === conversation.id ? (
                    <div className="flex gap-space-xs">
                      <input value={editingTitle} onChange={(event) => setEditingTitle(event.target.value)} className={`${cardCls} w-full px-space-sm py-space-xs text-body-sm`} />
                      <button type="button" onClick={() => handleRename(conversation.id)} className="rounded bg-primary-container px-space-sm py-1 text-label-sm text-on-primary">ذخیره</button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-space-xs">
                      <button type="button" onClick={() => setSelectedId(conversation.id)} className={`flex-1 rounded px-space-sm py-space-xs text-right text-body-sm ${selectedId === conversation.id ? 'bg-primary-container/10 font-bold' : ''}`}>{conversation.title || assistantPage.newChat}</button>
                      <button type="button" onClick={() => { setEditingId(conversation.id); setEditingTitle(conversation.title) }} className="text-body-sm">✎</button>
                      <button type="button" onClick={() => handleDelete(conversation.id)} className="text-body-sm">✕</button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  )
}

