import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import AuthLayout from '../components/AuthLayout.jsx'

const EMPTY = { name: '', email: '', username: '', phone: '', role: 'student', teacherCode: '', password: '', confirm: '' }

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setFieldErrors({})
    if (form.password !== form.confirm) {
      setFieldErrors({ confirm: 'Passwords do not match.' })
      return
    }
    setBusy(true)
    try {
      const { confirm, ...payload } = form
      await api('/auth/register', { method: 'POST', body: payload })
      navigate('/login', { state: { notice: 'Account created. Sign in to continue.' } })
    } catch (err) {
      setError(err.message)
      setFieldErrors(err.fields || {})
    } finally {
      setBusy(false)
    }
  }

  const field = (key, label, props = {}) => (
    <label>{label}
      <input value={form[key]} onChange={set(key)} aria-invalid={!!fieldErrors[key]} {...props} />
      {fieldErrors[key] && <span className="error">{fieldErrors[key]}</span>}
    </label>
  )

  return (
    <AuthLayout title="Create account" subtitle="Students see their own attendance. Teachers mark it.">
      <form onSubmit={onSubmit}>
        {field('name', 'Full name', { autoComplete: 'name', required: true })}
        {field('email', 'Email', { type: 'email', autoComplete: 'email', required: true })}
        {field('username', 'Username', { autoComplete: 'username', required: true })}
        {field('phone', 'Mobile number (with country code)', { type: 'tel', placeholder: '+919876543210', autoComplete: 'tel', required: true })}
        <label>I am a
          <select value={form.role} onChange={set('role')}>
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
          </select>
        </label>
        {form.role === 'teacher' && field('teacherCode', 'Teacher sign-up code', { required: true })}
        {field('password', 'Password', { type: 'password', autoComplete: 'new-password', required: true })}
        {field('confirm', 'Confirm password', { type: 'password', autoComplete: 'new-password', required: true })}
        {error && <p className="error" role="alert">{error}</p>}
        <button disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
      </form>
      <p className="links"><Link to="/login">Already have an account? Sign in</Link></p>
    </AuthLayout>
  )
}
