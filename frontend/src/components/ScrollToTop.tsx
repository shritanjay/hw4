import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Start every new page at the top (React Router keeps the old scroll position otherwise). */
export default function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}
