import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const MAIN_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Shop All' },
  { to: '/products?department=Classic+Yale', label: 'Classic Yale' },
  { to: '/products?department=Sports+%26+Game+Day', label: 'Sports' },
  { to: '/products?department=Family', label: 'Family' },
  { to: '/about', label: 'About Us' },
]

const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-link active' : 'nav-link')

export default function NavBar() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname, search } = useLocation()

  // React Router matches on the path only, so "?department=Family" links would all look active on /products.
  function isActive(to: string, end?: boolean) {
    const [path, query = ''] = to.split('?')
    if (path === '/products') {
      const dept = new URLSearchParams(search).get('department') ?? ''
      const want = new URLSearchParams(query).get('department') ?? ''
      return pathname === '/products' && dept === want
    }
    return end ? pathname === path : pathname.startsWith(path)
  }

  return (
    <header className="site-header">
      <div className="announce">
        Officially licensed Yale apparel · Visit us at <strong>57 Broadway, New Haven</strong>
      </div>
      <div className="nav">
        <NavLink to="/" className="brand" aria-label="Yale Bulldog Blue by Campus Customs, home">
          <span className="brand-name">Yale Bulldog Blue</span>
          <span className="brand-sub">by Campus Customs</span>
        </NavLink>
        <nav className="nav-links" aria-label="Main">
          {MAIN_LINKS.map((l) => (
            <NavLink
              key={l.label}
              to={l.to}
              className={() => (isActive(l.to, l.end) ? 'nav-link active' : 'nav-link')}
              aria-current={isActive(l.to, l.end) ? 'page' : undefined}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="nav-auth">
          {!ready ? null : user ? (
            <>
              <span className="nav-user">Hi, {user.first_name}</span>
              <button
                type="button"
                className="nav-link as-button"
                onClick={async () => {
                  await logout()
                  navigate('/')
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={linkClass}>
                Log in
              </NavLink>
              <NavLink to="/signup" className="nav-cta">
                Create account
              </NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
