import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice } from '../api'
import type { ProductDetail as Detail } from '../types'

function stockLabel(q: number) {
  if (q === 0) return 'Sold out'
  if (q <= 3) return `Only ${q} left`
  return `${q} in stock`
}

export default function ProductDetail() {
  const { id = '' } = useParams()
  const [item, setItem] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setItem(null)
    setError(null)
    fetchProduct(id).then(setItem).catch((e: Error) => setError(e.message))
  }, [id])

  if (error) {
    return (
      <section>
        <h1>{error === 'Not found' ? 'Product not found' : 'Something went wrong'}</h1>
        <Link to="/products">← Back to products</Link>
      </section>
    )
  }
  if (!item) return <p className="muted">Loading…</p>

  return (
    <section>
      <Link to="/products" className="back">← All products</Link>
      <div className="detail">
        <div className="detail-img">
          <img src={item.image_url} alt={item.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow">{item.category} · {item.garment_type}</p>
          <h1>{item.name}</h1>
          <p className="detail-price">{formatPrice(item.price)}</p>
          <p className="detail-desc">{item.description}</p>

          <h3>Colors</h3>
          <ul className="pills">
            {item.colors.map((c) => <li key={c}>{c}</li>)}
          </ul>

          <h3>Sizes & stock</h3>
          {item.sizes.length === 0 ? (
            <p className="muted">Stock information isn't available for this item.</p>
          ) : (
            <ul className="sizes">
              {item.sizes.map((s) => (
                <li key={s.size} className={s.in_stock ? (s.quantity <= 3 ? 'low' : '') : 'out'}>
                  <strong>{s.size}</strong>
                  <span>{stockLabel(s.quantity)}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="muted small-note">
            {item.total_stock > 0 ? `${item.total_stock} total across all sizes.` : 'Sold out in every size right now.'}
          </p>
        </div>
      </div>
    </section>
  )
}
