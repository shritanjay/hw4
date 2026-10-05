import type { ChatHistory, ChatMessage, ChatReply, PageContext, ProductDetail, ProductCard, User } from './types'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<ProductCard[]>('/api/products')
export const fetchProduct = (id: string) => getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (n: number) => `$${n.toFixed(2)}`

/** Chat with the shop assistant. Logged-in shoppers' history comes from the database; guests send theirs. */
export async function sendChat(message: string, history: ChatMessage[], page: PageContext): Promise<ChatReply> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history: history.slice(-20).map(({ role, content }) => ({ role, content })), page }),
  })
  if (!res.ok) throw new Error(`Chat failed (${res.status})`)
  return res.json() as Promise<ChatReply>
}

// ---- Accounts (session is an HttpOnly cookie set by the backend) ----

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${res.status})`)
  }
  return (res.status === 204 ? null : await res.json()) as T
}

export interface SignupForm {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

export const signup = (form: SignupForm) => postJson<User>('/api/auth/signup', form)
export const login = (email: string, password: string) => postJson<User>('/api/auth/login', { email, password })
export const logout = () => postJson<null>('/api/auth/logout', {})
export const fetchMe = () => getJson<User | null>('/api/auth/me')

export const fetchChatHistory = () => getJson<ChatHistory>('/api/chat/history')

export async function clearChatHistory(): Promise<void> {
  const res = await fetch('/api/chat/history', { method: 'DELETE' })
  if (!res.ok) throw new Error(`Couldn't clear history (${res.status})`)
}
