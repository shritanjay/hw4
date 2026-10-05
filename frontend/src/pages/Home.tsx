import { Link } from 'react-router-dom'

// Tees first: the most affordable way in ($32), then up to outerwear.
const CATEGORIES = [
  { label: 'Tees', price: 'from $32', blurb: 'Everyday cotton with a little Bulldog attitude.' },
  { label: 'Long sleeves', price: 'from $45', blurb: 'Light layers for early-fall walks.' },
  { label: 'Crewnecks', price: 'from $45', blurb: 'The classic layer for lectures and late nights.' },
  { label: 'Hoodies', price: 'from $45', blurb: 'Heavy, warm, built for Old Campus.' },
  { label: 'Quarter-zips', price: '$72', blurb: 'Sharp for a seminar, easy for the weekend.' },
  { label: 'Jackets', price: 'from $88', blurb: 'Fleece and outerwear for a New England winter.' },
]

const DEPARTMENTS = [
  { name: 'Classic Yale', text: 'Wordmarks, vintage bulldogs and everyday Yale blue.' },
  { name: 'Sports & Game Day', text: 'Varsity teams from hockey to sailing, plus Harvard–Yale gear.' },
  { name: 'Residential Colleges', text: 'Wear your college crest, from Branford to Trumbull.' },
  { name: 'Grad & Professional Schools', text: 'School of Management, Law, Medicine, Nursing, Art, Music and more.' },
  { name: 'Family', text: 'Yale Mom, Dad, Grandpa and the rest of the cheering section.' },
]

const shopLink = (key: string, value: string) => `/products?${new URLSearchParams({ [key]: value })}`

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="eyebrow">Officially licensed · New Haven, CT</p>
          <h1>Wear the blue. Bring the Bulldog home.</h1>
          <p className="lede">
            Yale apparel picked out on Broadway, from your first-year tee to the crewneck you wear back to reunion.
          </p>
          <div className="hero-actions">
            <Link to={shopLink('category', 'Tees')} className="btn">Shop tees from $32</Link>
            <Link to="/products" className="btn ghost">Shop all 102 items</Link>
          </div>
        </div>
        <div className="hero-mark" aria-hidden>Y</div>
      </section>

      <section>
        <div className="section-head">
          <h2 className="section-title">Shop by department</h2>
          <Link to="/products">View all →</Link>
        </div>
        <div className="dept-grid">
          {DEPARTMENTS.map((d) => (
            <Link key={d.name} to={shopLink('department', d.name)} className="dept-tile">
              <strong>{d.name}</strong>
              <span>{d.text}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="feature">
        <p className="eyebrow">Game day</p>
        <h2>Harvard–Yale season is here</h2>
        <p className="muted">The rivalry comes around every November. Gear up and keep the stands loud.</p>
        <Link to={shopLink('q', 'harvard')}>See rivalry gear →</Link>
      </section>

      <section>
        <h2 className="section-title">Shop by style</h2>
        <div className="tile-grid">
          {CATEGORIES.map((c) => (
            <Link key={c.label} to={shopLink('category', c.label)} className="tile">
              <strong>
                {c.label} <em>{c.price}</em>
              </strong>
              <span>{c.blurb}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="feature chat-teaser">
        <h2>Not sure what fits?</h2>
        <p className="muted">
          Ask our shop assistant for gift ideas, colors, or whether your size is in stock. It checks the real
          inventory, so it won't guess.
        </p>
      </section>
    </>
  )
}
