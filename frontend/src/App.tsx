import { Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar'
import ChatWidget from './components/ChatWidget'
import ChatResultsPanel from './components/ChatResultsPanel'
import ScrollToTop from './components/ScrollToTop'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import Signup from './pages/Signup'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <div className="app">
      <ScrollToTop />
      <NavBar />
      <main className="page">
        <ChatResultsPanel />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="footer">
        Yale Bulldog Blue by Campus Customs · 57 Broadway, New Haven, CT · Class demo, not affiliated
      </footer>
      <ChatWidget />
    </div>
  )
}
