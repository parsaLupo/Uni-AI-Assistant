/**
 * /assistant (+ /conversations/:id) — Smart Assistant chat surface.
 *
 * UX contract (chat UX fixes, Parts 2–3):
 * - Opening /assistant presents a fresh, immediately usable composer — the
 *   «گفتگوی جدید» button is never a prerequisite for typing. The first
 *   submitted message creates the conversation through the existing
 *   POST /conversations flow and then sends the message through the existing
 *   POST /conversations/:id/messages/ endpoint, so ownership, citations and
 *   persistence stay identical. The backend titles the fresh conversation
 *   with the first message (views.create_message) — no client title logic.
 * - Only the message list scrolls inside the bounded chat card; the shell,
 *   page header, composer and history stay in place. Near the bottom the
 *   view follows new messages; a reader scrolled up is never yanked down.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { EmptyState, LoadingState, PageHeader, cardCls } from '../../components/ui'
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

/** Local stand-in for a message whose server row does not exist yet. */
function makePending(content: string): Message {
  return {
    id: -Date.now(),
    conversation: 0,
    role: 'USER',
    content,
    retrieval_mode: '',
    insufficient_evidence: false,
    latency_ms: null,
    created_at: '',
    sources: [],
  }
}

export function AssistantPage() {
  const { status: authStatus } = useAuth()
  const navigate = useNavigate()
  const params = useParams()
  // `/conversations/:id` deep-links straight into one conversation. The shell
  // remounts the page on navigation (key=pathname), and the effect below
  // keeps the selection in sync even if that key ever goes away.
  const routeId = params.id ? Number(params.id) : null
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(
    routeId !== null && Number.isFinite(routeId) ? routeId : null,
  )
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  // Conversations whose messages are managed locally: when the first message
  // of a brand-new conversation is in flight (or failed), the server detail
  // must not be refetched and clobber the local state. React flushes effects
  // after all microtasks, so a per-send flag would already be cleared by the
  // time the loader runs — this set lives for the mount's lifetime instead.
  const managedIdsRef = useRef<Set<number>>(new Set())

  // Chat scrolling: the message list is the only scrolling element. When the
  // user is near the bottom new messages keep the view pinned; scrolled-up
  // readers are left alone.
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickRef = useRef(true)
  // Synchronous double-submit guard: state updates batch, so two submits in
  // one tick would both read `sending` as false. A ref never lags.
  const sendingRef = useRef(false)

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
      })
      .catch(() => {
        if (!cancelled) setError(assistantPage.errorList)
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
    // A locally managed conversation (created in this session) owns its
    // message state; refetching would race the optimistic updates.
    if (selectedId !== null && managedIdsRef.current.has(selectedId)) return
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

  // A freshly opened conversation always starts at its latest message.
  useEffect(() => {
    stickRef.current = true
  }, [selectedId])

  // The route is authoritative for the selection: /assistant means a fresh
  // surface, /conversations/:id means that conversation.
  useEffect(() => {
    const target = routeId !== null && Number.isFinite(routeId) ? routeId : null
    setSelectedId((current) => (current === target ? current : target))
  }, [routeId])

  useEffect(() => {
    const element = scrollRef.current
    if (element && stickRef.current) element.scrollTop = element.scrollHeight
  }, [messages, sending, selectedId])

  const keepBottomWhileNearBottom = () => {
    const element = scrollRef.current
    if (!element) return
    stickRef.current =
      element.scrollHeight - element.scrollTop - element.clientHeight < 80
  }

  function handleNewChat() {
    if (authStatus !== 'authenticated') {
      navigate('/login')
      return
    }
    // A fresh surface: no conversation is created until the first message is
    // actually sent, so no empty conversations pile up in the history.
    setSelectedId(null)
    setMessages([])
    setInput('')
    setError(null)
    setEditingId(null)
    if (routeId !== null) navigate('/assistant')
  }

  async function handleRename(id: number) {
    try {
      const updated = await renameConversation(id, editingTitle.trim() || 'گفتگو')
      setConversations((prev) => prev.map((item) => (item.id === id ? updated : item)))
      setEditingId(null)
    } catch {
      setError(assistantPage.errorAction)
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteConversation(id)
      setConversations((prev) => prev.filter((item) => item.id !== id))
      if (selectedId === id) {
        setSelectedId(null)
        setMessages([])
        setInput('')
        if (routeId !== null) navigate('/assistant')
      }
    } catch {
      setError(assistantPage.errorAction)
    }
  }

  async function handleSend(event: FormEvent) {
    event.preventDefault()
    if (authStatus !== 'authenticated') {
      navigate('/login')
      return
    }
    const content = input.trim()
    if (!content || sending || sendingRef.current) return
    sendingRef.current = true
    setInput('')
    setError(null)
    setSending(true)
    const pending = makePending(content)
    setMessages((prev) => [...prev, pending])
    stickRef.current = true
    try {
      let conversationId = selectedId
      let createdConversation = false
      if (conversationId === null) {
        // First message on a fresh surface: create the conversation through
        // the normal flow, show it in the history immediately, then send.
        const conversation = await createConversation()
        conversationId = conversation.id
        createdConversation = true
        setConversations((prev) => [conversation, ...prev])
        managedIdsRef.current.add(conversationId)
        setSelectedId(conversationId)
      }
      const result = await sendMessage(conversationId, content)
      setMessages((prev) => [
        ...prev.filter((item) => item.id !== pending.id),
        result.user_message,
        result.message,
      ])
      stickRef.current = true
      if (createdConversation) {
        // The backend titles a fresh conversation with its first message; a
        // quiet refresh makes that title visible right away.
        listConversations()
          .then((items) => setConversations(items))
          .catch(() => undefined)
      }
    } catch {
      // Never lose the typed message: put it back and drop the bubble.
      setMessages((prev) => prev.filter((item) => item.id !== pending.id))
      setInput(content)
      setError(assistantPage.errorSend)
    } finally {
      setSending(false)
      sendingRef.current = false
    }
  }

  async function handleRetry() {
    const lastUser = [...messages].reverse().find((item) => item.role === 'USER')
    if (!lastUser) return
    setInput(lastUser.content)
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-space-lg px-gutter-desktop pt-space-lg">
      <PageHeader
        title={assistantPage.title}
        subtitle={assistantPage.subtitle}
        actions={
          <button
            type="button"
            onClick={handleNewChat}
            className="flex items-center justify-center gap-space-xs rounded bg-primary-container px-space-md py-2 text-label-lg font-semibold text-on-primary transition-colors hover:bg-[#2563EB]"
          >
            <span aria-hidden="true" className="material-symbols-outlined text-[20px]">
              add_comment
            </span>
            {assistantPage.newChat}
          </button>
        }
      />
      <div className="grid min-h-0 flex-1 grid-cols-1 grid-rows-[minmax(0,1.7fr)_minmax(0,1fr)] gap-space-lg lg:grid-cols-[minmax(0,1fr)_18rem] lg:grid-rows-1">
        <section
          className={`${cardCls} flex min-h-0 flex-col overflow-hidden p-space-lg`}
          aria-label={assistantPage.title}
        >
          {/* The one vertical scroller: messages. The composer below stays put. */}
          <div
            ref={scrollRef}
            onScroll={keepBottomWhileNearBottom}
            className="flex min-h-0 flex-1 flex-col gap-space-md overflow-y-auto"
          >
            {selectedId === null ? (
              <div className="flex flex-col items-center gap-space-sm rounded-xl bg-surface-container-low px-space-lg py-space-xl text-center">
                <h2 className="m-0 text-headline-md font-bold text-on-surface">{assistantPage.welcomeTitle}</h2>
                <p className="m-0 max-w-lg text-body-sm text-on-surface-variant">{assistantPage.welcomeBody}</p>
              </div>
            ) : messages.length === 0 && !sending ? (
              <EmptyState message={assistantPage.noHistory} />
            ) : (
              messages.map((message) => (
                <article
                  key={message.id}
                  className={`rounded-xl p-space-md ${message.role === 'USER' ? 'bg-primary-container/10' : message.insufficient_evidence ? 'border border-[#FDE68A] bg-[#FFFBEB]' : 'bg-surface-container-low'}`}
                >
                  <p className="m-0 min-w-0 whitespace-pre-wrap break-words text-body-sm text-on-surface">{message.content}</p>
                  {message.insufficient_evidence ? <p className="mt-space-xs text-body-sm font-bold text-[#92400E]">شواهد کافی برای پاسخ قطعی یافت نشد.</p> : null}
                  {message.role === 'ASSISTANT' && message.sources?.length ? (
                    <ul className="mt-space-sm flex min-w-0 flex-col gap-space-xs">
                      {message.sources.map((source) => (
                        <li key={source.id} className="min-w-0 break-words text-body-sm text-on-surface-variant">{source.source_label} — صفحه {source.page} — {source.section}</li>
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
              ))
            )}
            {sending ? (
              <div role="status" aria-live="polite" className="flex items-center gap-space-sm text-body-sm text-on-surface-variant">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-outline-variant border-t-primary motion-reduce:animate-none" />
                {assistantPage.sending}
              </div>
            ) : null}
          </div>
          {error ? (
            <div role="status" aria-live="polite" className="mt-space-md shrink-0 rounded-xl border border-[#FDE68A] bg-[#FFFBEB] px-space-md py-space-sm text-body-sm text-[#92400E]">{error}</div>
          ) : null}
          <form className="mt-space-md flex shrink-0 items-end gap-space-sm" onSubmit={handleSend}>
            <label htmlFor="assistant-composer" className="sr-only">{assistantPage.composerPlaceholder}</label>
            <textarea
              id="assistant-composer"
              dir="auto"
              rows={2}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={sending}
              placeholder={assistantPage.composerPlaceholder}
              className={`${cardCls} min-h-[3rem] w-full resize-y px-space-md py-space-sm text-body-sm`}
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="flex shrink-0 items-center justify-center gap-space-xs rounded bg-primary-container px-space-lg py-3 text-label-lg font-semibold text-on-primary transition-colors hover:bg-[#2563EB] disabled:opacity-75"
            >
              {sending ? assistantPage.sending : assistantPage.send}
            </button>
          </form>
        </section>
        <aside className={`${cardCls} flex min-h-0 flex-col overflow-hidden p-space-md`} aria-label={assistantPage.history}>
          <h3 className="m-0 shrink-0 text-label-lg font-bold text-on-surface">{assistantPage.history}</h3>
          {loading ? (
            <LoadingState />
          ) : conversations.length === 0 ? (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <EmptyState message={assistantPage.noHistory} />
            </div>
          ) : (
            <ul className="flex min-h-0 flex-1 flex-col gap-space-xs overflow-y-auto">
              {conversations.map((conversation) => (
                <li key={conversation.id} className="flex flex-col gap-space-xs">
                  {editingId === conversation.id ? (
                    <div className="flex gap-space-xs">
                      <input
                        value={editingTitle}
                        onChange={(event) => setEditingTitle(event.target.value)}
                        aria-label={assistantPage.renameTitle}
                        className={`${cardCls} w-full px-space-sm py-space-xs text-body-sm`}
                      />
                      <button type="button" onClick={() => handleRename(conversation.id)} className="rounded bg-primary-container px-space-sm py-1 text-label-sm text-on-primary">{assistantPage.save}</button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-space-xs">
                      <button
                        type="button"
                        onClick={() => navigate(`/conversations/${conversation.id}`)}
                        className={`min-w-0 flex-1 rounded px-space-sm py-space-xs text-right text-body-sm ${selectedId === conversation.id ? 'bg-primary-container/10 font-bold' : ''}`}
                      >
                        <span className="block truncate">{conversation.title || assistantPage.newChat}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => { setEditingId(conversation.id); setEditingTitle(conversation.title) }}
                        aria-label={assistantPage.renameTitle}
                        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-primary"
                      >
                        <span aria-hidden="true" className="material-symbols-outlined text-[18px]">edit</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(conversation.id)}
                        aria-label={assistantPage.deleteConversation}
                        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-error-container/60 hover:text-error"
                      >
                        <span aria-hidden="true" className="material-symbols-outlined text-[18px]">delete</span>
                      </button>
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
