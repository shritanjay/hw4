import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { PageResults } from './types'

/** Shared state so a chat reply can put product cards on the page. */
interface ChatResultsState {
  results: PageResults | null
  show: (results: PageResults) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(null)
  const value: ChatResultsState = {
    results,
    show: (r) => {
      setResults(r)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    clear: () => setResults(null),
  }
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
