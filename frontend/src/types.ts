export interface SizeStock {
  size: string
  quantity: number
  in_stock: boolean
}

export interface ProductCard {
  product_id: string
  name: string
  category: string
  department: string
  garment_type: string
  price: number
  short_description: string
  image_url: string
  in_stock: boolean
  sizes_in_stock: string[]
}

export interface ProductDetail extends ProductCard {
  description: string
  colors: string[]
  search_tags: string[]
  sizes: SizeStock[]
  total_stock: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: ProductCard[]
  created_at?: string | null
}

/** Where the shopper is when they send a message, so "this one" can be resolved. */
export interface PageContext {
  path: string
  product_id: string | null
  results_title: string | null
}

export interface ChatHistory {
  logged_in: boolean
  messages: ChatMessage[]
}

/** Search matches the chat asks the page to show (built from the database by the backend). */
export interface PageResults {
  title: string
  query: string
  total: number
  products: ProductCard[]
}

export interface ChatReply {
  reply: string
  products: ProductCard[]
  page: PageResults | null
  redacted: string[]
  user_message: string | null
}

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
  created_at?: string | null
}
