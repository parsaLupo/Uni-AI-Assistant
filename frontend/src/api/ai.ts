import { buildApiUrl, requestJson } from './client'

export interface AskResponse {
  mode: string
  answer: string
  sources: Array<Record<string, unknown>>
  insufficient_evidence: boolean
}

export interface AskStreamHandlers {
  onToken?: (text: string) => void
  onDone?: (result: AskResponse) => void
  onError?: (error: unknown) => void
}

export async function streamAsk(
  question: string,
  handlers: AskStreamHandlers = {},
  signal?: AbortSignal,
): Promise<void> {
  if (!('ReadableStream' in globalThis) || !('TextDecoder' in globalThis)) {
    const result = await requestJson<AskResponse>('/ai/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    })
    handlers.onToken?.(result.answer)
    handlers.onDone?.(result)
    return
  }

  const response = await fetch(buildApiUrl('/ai/ask/stream'), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ question }),
    signal,
  })

  if (!response.ok || !response.body) {
    const result = await requestJson<AskResponse>('/ai/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    })
    handlers.onToken?.(result.answer)
    handlers.onDone?.(result)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventName = 'message'

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) {
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('event:')) eventName = line.slice(6).trim()
          else if (line.startsWith('data:')) {
            const raw = line.slice(5).trim()
            if (!raw) continue
            const parsed = JSON.parse(raw) as Record<string, unknown>
            if (eventName === 'token') handlers.onToken?.(String(parsed.text ?? ''))
            else if (eventName === 'done') handlers.onDone?.(parsed as unknown as AskResponse)
            else if (eventName === 'error') handlers.onError?.(parsed)
          }
        }
        eventName = 'message'
      }
    }
  } catch (error) {
    handlers.onError?.(error)
  }
}
