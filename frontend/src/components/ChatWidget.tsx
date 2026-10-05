import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import Markdown from 'react-markdown'
import { Link, useLocation } from 'react-router-dom'
import { clearChatHistory, fetchChatHistory, formatPrice, sendChat } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import YaleThinking from './YaleThinking'
import type { ChatMessage, PageContext } from '../types'

const GREETING: ChatMessage = {
  role: 'assistant',
  content: "Hi! I'm the Campus Customs shop assistant. Ask me about gifts, colors, prices, or whether your size is in stock.",
}

function greeting(firstName?: string): ChatMessage {
  return firstName
    ? { role: 'assistant', content: `Welcome back, ${firstName}! Ask me about gifts, colors, prices, or whether your size is in stock.` }
    : GREETING
}

const HOME_SUGGESTIONS = ['What t-shirts do you have?', 'Gift for a Yale mom', 'Navy hoodies under $70']
const PRODUCT_SUGGESTIONS = ['Is this in M?', 'What sizes are left?', 'Do you have this in another color?']
const RESULTS_SUGGESTIONS = ['Which of these is cheapest?', 'Any of these in XL?']

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const { results, show } = useChatResults()
  const { user, ready } = useAuth()
  const { pathname } = useLocation()
  const [savedCount, setSavedCount] = useState(0)

  // Customer memory: when a shopper logs in (or the page loads while logged in), reload their saved chat.
  // On logout, start fresh so the next person on this browser doesn't see it.
  useEffect(() => {
    if (!ready) return
    let cancelled = false
    if (!user) {
      setMessages([GREETING])
      setSavedCount(0)
      return
    }
    fetchChatHistory()
      .then((h) => {
        if (cancelled) return
        setMessages([greeting(user.first_name), ...h.messages])
        setSavedCount(h.messages.length)
      })
      .catch(() => !cancelled && setMessages([greeting(user.first_name)]))
    return () => {
      cancelled = true
    }
  }, [user, ready])

  const onProductPage = /^\/products\/[^/]+$/.test(pathname)
  const suggestions = onProductPage ? PRODUCT_SUGGESTIONS : results ? RESULTS_SUGGESTIONS : HOME_SUGGESTIONS
  const inputRef = useRef<HTMLInputElement>(null)

  // Esc closes the panel; opening it puts the cursor in the input.
  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  function pageContext(): PageContext {
    const match = pathname.match(/^\/products\/([^/]+)$/)
    return {
      path: pathname,
      product_id: match ? decodeURIComponent(match[1]) : null,
      results_title: results?.title ?? null,
    }
  }

  async function onClearHistory() {
    if (!window.confirm('Delete your saved chat history?')) return
    await clearChatHistory()
    setMessages([greeting(user?.first_name)])
    setSavedCount(0)
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy, open])

  async function send(text: string) {
    const message = text.trim()
    if (!message || busy) return
    const history = messages.slice(1) // skip the canned greeting
    setMessages((m) => [...m, { role: 'user', content: message }])
    setInput('')
    setBusy(true)
    try {
      const res = await sendChat(message, history, pageContext())
      setMessages((m) => {
        const next = [...m]
        if (res.user_message) {
          // The backend removed sensitive data; show the shopper what was actually kept.
          next[next.length - 1] = { role: 'user', content: res.user_message }
        }
        const note = res.redacted.length
          ? [{ role: 'assistant' as const, content: `🔒 For your safety I removed the ${res.redacted.join(', ')} from your message. It was not saved or sent to the assistant.` }]
          : []
        return [...next, ...note, { role: 'assistant', content: res.reply, products: res.products }]
      })
      if (res.page) show(res.page) // search results go onto the page as product cards
      if (user) setSavedCount((c) => c + 2) // the backend saved this question + answer
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: "Sorry, I couldn't reach the shop right now. Please try again." }])
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  return (
    <div className="chat-widget">
      {open && (
        <section className="chat-panel" aria-label="Shop assistant chat">
          <header className="chat-header">
            <div>
              <strong><span className="yale-tile small" aria-hidden>Yale</span> Shop assistant</strong>
              <span>
                {user ? `Chatting as ${user.first_name}` : 'Campus Customs · checks live stock'}
                {user ? ` · ${savedCount ? `${savedCount} saved messages` : 'your chat will be saved'}` : ''}
              </span>
            </div>
            <div className="chat-header-actions">
              {user && messages.length > 1 && (
                <button type="button" className="link-button muted" onClick={() => void onClearHistory()}>
                  Clear history
                </button>
              )}
              <button type="button" className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
            </div>
          </header>

          <div className="chat-log">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <div className="bubble">
                  {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : <p>{m.content}</p>}
                </div>
                {!!m.products?.length && (
                  <div className="msg-products">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="mini-card">
                        <img src={p.image_url} alt="" />
                        <span>{p.name}<em>{formatPrice(p.price)}</em></span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && (
              <div className="msg assistant typing">
                <YaleThinking />
              </div>
            )}
            {!busy && (
              <div className="chat-suggestions" aria-label="Suggested questions">
                {suggestions.map((s) => (
                  <button key={s} type="button" onClick={() => void send(s)}>{s}</button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form className="chat-input" onSubmit={onSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about merch…"
              aria-label="Message"
              disabled={busy}
              ref={inputRef}
            />
            <button type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </section>
      )}

      <button type="button" className="chat-fab" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? 'Close' : 'Chat with us'}
      </button>
    </div>
  )
}
