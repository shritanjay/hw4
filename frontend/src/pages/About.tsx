import { Link } from 'react-router-dom'

export default function About() {
  return (
    <section className="prose">
      <p className="eyebrow">About Us</p>
      <h1>A neighborhood shop with a whole lot of blue</h1>
      <p>
        Yale Bulldog Blue by Campus Customs is a Yale apparel shop at 57 Broadway, a short walk from
        campus. We stock officially licensed gear for every corner of the Yale community: students
        moving in, varsity fans, residential college loyalists, grad and professional school
        families, and alumni coming back for one more weekend in New Haven.
      </p>

      <h2>What we carry</h2>
      <p>
        Hoodies, crewnecks, quarter-zips, tees and jackets, plus designs for sports teams,
        graduate schools and the proud parents and grandparents who wear Yale too. Sizes run XS to
        XXL, and our shop assistant can check which sizes are on the shelf right now.
      </p>

      <h2>Visit or get in touch</h2>
      <ul className="facts">
        <li><span>Shop</span>57 Broadway, New Haven, CT 06511</li>
        <li><span>Orders</span>orderdept@campuscustoms.com</li>
        <li><span>Phone</span>(475) 301-4205</li>
      </ul>

      <h2>Returns, simply put</h2>
      <p>
        Changed your mind? You have 30 days from shipping to send back unworn items with the tags
        still on. Custom-made pieces are final sale. If we made the mistake, return shipping is on
        us. Refunds land within about 2–10 business days and don't include the original shipping.
      </p>

      <p className="muted small">
        This site is a classroom project for Yale SOM. Campus Customs is used as a local setting;
        it is not a partnership with the shop.
      </p>
      <Link to="/products" className="btn">Browse the collection</Link>
    </section>
  )
}
