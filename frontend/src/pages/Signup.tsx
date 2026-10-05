import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const MIN_LEN = 8

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirm_password: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const tooShort = form.password.length > 0 && form.password.length < MIN_LEN
  const mismatch = form.confirm_password.length > 0 && form.password !== form.confirm_password
  const matches = form.confirm_password.length > 0 && form.password === form.confirm_password

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password.length < MIN_LEN) return setError(`Password must be at least ${MIN_LEN} characters.`)
    if (form.password !== form.confirm_password) return setError("Passwords don't match.")
    setBusy(true)
    try {
      await signup(form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-card">
      <h1>Create account</h1>
      <p className="muted">Save your chats with the shop assistant and get back to them anytime.</p>
      <form className="form" onSubmit={onSubmit} noValidate>
        <div className="row">
          <label>First name<input value={form.first_name} onChange={set('first_name')} autoComplete="given-name" required /></label>
          <label>Last name<input value={form.last_name} onChange={set('last_name')} autoComplete="family-name" required /></label>
        </div>
        <label>Email<input type="email" value={form.email} onChange={set('email')} autoComplete="email" required /></label>
        <label>
          Password
          <input type="password" value={form.password} onChange={set('password')} autoComplete="new-password" required />
          <span className={tooShort ? 'hint bad' : 'hint'}>At least {MIN_LEN} characters</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            value={form.confirm_password}
            onChange={set('confirm_password')}
            autoComplete="new-password"
            aria-invalid={mismatch}
            className={mismatch ? 'invalid' : matches ? 'valid' : ''}
            required
          />
          {mismatch && <span className="hint bad">Passwords don't match</span>}
          {matches && <span className="hint good">Passwords match ✓</span>}
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button
          type="submit"
          className="btn"
          disabled={busy || !form.first_name || !form.last_name || !form.email || !form.password || !matches || tooShort}
        >
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">Already have one? <Link to="/login">Log in</Link></p>
    </section>
  )
}
