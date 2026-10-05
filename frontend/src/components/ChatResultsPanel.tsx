import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

/** Product cards the shop assistant found, shown at the top of whatever page the shopper is on.
 *  On a single-item page it shrinks to a one-line bar so the item's detail view stays at the top. */
export default function ChatResultsPanel() {
  const { results, clear } = useChatResults()
  const { pathname } = useLocation()
  const [expandedOn, setExpandedOn] = useState<string | null>(null)
  if (!results) return null

  const onItemPage = pathname.startsWith('/products/')
  const collapsed = onItemPage && expandedOn !== pathname
  const count = `${results.total} ${results.total === 1 ? 'item' : 'items'}`

  if (collapsed) {
    return (
      <div className="chat-results-bar" aria-label="Results from chat">
        <span>
          <span className="eyebrow">From your chat</span> {results.title} · {count}
        </span>
        <span className="bar-actions">
          <button type="button" className="link-button" onClick={() => setExpandedOn(pathname)}>
            Show results
          </button>
          <button type="button" className="link-button muted" onClick={clear}>
            Clear
          </button>
        </span>
      </div>
    )
  }

  return (
    <section className="chat-results" aria-live="polite" aria-label="Results from chat">
      <div className="chat-results-head">
        <div>
          <p className="eyebrow">From your chat</p>
          <h2>{results.title}</h2>
          <p className="muted">
            {count} · for “{results.query}”
          </p>
        </div>
        <div className="bar-actions">
          {onItemPage && (
            <button type="button" className="btn ghost" onClick={() => setExpandedOn(null)}>
              Hide
            </button>
          )}
          <button type="button" className="btn ghost" onClick={clear}>
            Clear results
          </button>
        </div>
      </div>
      <div className="grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
