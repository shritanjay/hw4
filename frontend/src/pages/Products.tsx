import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductCard as Product } from '../types'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
// Same order the backend uses: cheapest everyday items first.
const CATEGORY_ORDER = ['Tees', 'Long sleeves', 'Crewnecks', 'Hoodies', 'Quarter-zips', 'Jackets']
const DEPARTMENTS = ['Classic Yale', 'Sports & Game Day', 'Residential Colleges', 'Grad & Professional Schools', 'Family']
const DEPARTMENT_HINT: Record<string, string> = {
  'Grad & Professional Schools': 'School of Management, Law, Medicine, Nursing, Art, Music and more',
  'Residential Colleges': 'Crests from Branford to Trumbull',
  Family: 'Yale Mom, Dad, Grandpa and the whole crew',
  'Sports & Game Day': 'Varsity teams and Harvard–Yale',
  'Classic Yale': 'Wordmarks, bulldogs and everyday Yale',
}
const SORTS = {
  featured: { label: 'Featured: tees first', fn: () => 0 }, // keep the API's shop order
  'price-asc': { label: 'Price: low to high', fn: (a: Product, b: Product) => a.price - b.price || a.name.localeCompare(b.name) },
  'price-desc': { label: 'Price: high to low', fn: (a: Product, b: Product) => b.price - a.price || a.name.localeCompare(b.name) },
  name: { label: 'Name A–Z', fn: (a: Product, b: Product) => a.name.localeCompare(b.name) },
} as const
type SortKey = keyof typeof SORTS

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const category = params.get('category') ?? 'All'
  const department = params.get('department') ?? 'All'
  const size = params.get('size') ?? ''
  const inStockOnly = params.get('instock') === '1'
  const sort = (params.get('sort') ?? 'featured') as SortKey

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const categories = useMemo(() => {
    const present = new Set(products.map((p) => p.category))
    return ['All', ...CATEGORY_ORDER.filter((c) => present.has(c)), ...[...present].filter((c) => !CATEGORY_ORDER.includes(c))]
  }, [products])
  const deptCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const p of products) counts[p.department] = (counts[p.department] ?? 0) + 1
    return counts
  }, [products])

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return products
      .filter(
        (p) =>
          (category === 'All' || p.category === category) &&
          (department === 'All' || p.department === department) &&
          (!needle || `${p.name} ${p.garment_type} ${p.short_description}`.toLowerCase().includes(needle)) &&
          (!size || p.sizes_in_stock.includes(size)) &&
          (!inStockOnly || p.in_stock),
      )
      .sort((SORTS[sort] ?? SORTS.featured).fn)
  }, [products, q, category, department, size, inStockOnly, sort])

  function update(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value && value !== 'All' && value !== 'featured') next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const filtersOn = !!(q || category !== 'All' || department !== 'All' || size || inStockOnly)

  return (
    <section>
      <div className="products-head">
        <div>
          <p className="eyebrow">Shop</p>
          <h1>{department !== 'All' ? department : category !== 'All' ? category : 'All products'}</h1>
          <p className="muted">
            {loading ? 'Loading the catalogue…' : `${shown.length} of ${products.length} items`}
            {size && !loading ? ` · in stock in ${size}` : ''}
          </p>
        </div>
        <input
          className="search"
          type="search"
          placeholder="Search hoodies, Harvard, mom…"
          value={q}
          onChange={(e) => update('q', e.target.value)}
          aria-label="Search products"
        />
      </div>

      <nav className="departments" aria-label="Departments">
        <button type="button" className={department === 'All' ? 'dept active' : 'dept'} aria-pressed={department === 'All'} onClick={() => update('department', 'All')}>
          <strong>All departments</strong>
          <span>{products.length} items</span>
        </button>
        {DEPARTMENTS.map((d) => (
          <button key={d} type="button" className={d === department ? 'dept active' : 'dept'} aria-pressed={d === department} onClick={() => update('department', d)} title={DEPARTMENT_HINT[d]}>
            <strong>{d}</strong>
            <span>{deptCounts[d] ?? 0} items</span>
          </button>
        ))}
      </nav>
      {department !== 'All' && <p className="dept-hint muted">{DEPARTMENT_HINT[department]}</p>}

      <div className="chips" role="group" aria-label="Categories">
        {categories.map((c) => (
          <button key={c} type="button" className={c === category ? 'chip active' : 'chip'} aria-pressed={c === category} onClick={() => update('category', c)}>
            {c}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <div className="size-filter" role="group" aria-label="Show items in stock in size">
          <span className="toolbar-label">My size</span>
          {SIZES.map((s) => (
            <button
              key={s}
              type="button"
              className={s === size ? 'size-chip active' : 'size-chip'}
              aria-pressed={s === size}
              onClick={() => update('size', s === size ? '' : s)}
            >
              {s}
            </button>
          ))}
        </div>
        <label className="check">
          <input type="checkbox" checked={inStockOnly} onChange={(e) => update('instock', e.target.checked ? '1' : '')} />
          In stock only
        </label>
        <label className="sort">
          <span className="toolbar-label">Sort</span>
          <select value={sort} onChange={(e) => update('sort', e.target.value)}>
            {Object.entries(SORTS).map(([key, s]) => (
              <option key={key} value={key}>{s.label}</option>
            ))}
          </select>
        </label>
        {filtersOn && (
          <button type="button" className="link-button" onClick={() => setParams(sort !== 'featured' ? { sort } : {}, { replace: true })}>
            Reset filters
          </button>
        )}
      </div>

      {error && <p className="error">Couldn't load products: {error}. Is the backend running?</p>}

      {loading && (
        <div className="grid" aria-hidden>
          {Array.from({ length: 8 }, (_, i) => <div key={i} className="card skeleton" />)}
        </div>
      )}

      {!loading && !error && shown.length === 0 && (
        <div className="empty">
          <p>No products match{size ? ` in size ${size}` : ''}.</p>
          <button type="button" className="btn ghost" onClick={() => setParams({}, { replace: true })}>Clear all filters</button>
        </div>
      )}

      <div className="grid">
        {shown.map((p) => (
          <ProductCard key={p.product_id} product={p} highlightSize={size || undefined} />
        ))}
      </div>
    </section>
  )
}
