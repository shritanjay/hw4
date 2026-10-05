import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import type { ProductCard as Product } from '../types'

export default function ProductCard({ product, highlightSize }: { product: Product; highlightSize?: string }) {
  const few = product.in_stock && product.sizes_in_stock.length > 0 && product.sizes_in_stock.length <= 2
  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {!product.in_stock && <span className="badge">Sold out</span>}
        {highlightSize && product.sizes_in_stock.includes(highlightSize) && (
          <span className="badge ok">{highlightSize} in stock</span>
        )}
      </div>
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="card-price">{formatPrice(product.price)}</p>
        <p className="card-desc">{product.short_description}</p>
        {product.sizes_in_stock.length > 0 && (
          <p className={few ? 'card-sizes few' : 'card-sizes'}>
            {few ? `Only ${product.sizes_in_stock.join(', ')} left` : `Sizes: ${product.sizes_in_stock.join(' · ')}`}
          </p>
        )}
      </div>
    </Link>
  )
}
