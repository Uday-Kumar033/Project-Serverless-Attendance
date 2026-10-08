import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import AuthLayout from '../components/AuthLayout.jsx'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [step, setStep] = useState('phone') // 'phone' -> 'code'
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [fieldError, setFieldError] = useState('')
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown(cooldown - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  async function sendCode(e) {
    e?.preventDefault()
    setError(''); setNotice(''); setBusy(true)
    try {
      const res = await api('/auth/forgot', { method: 'POST', body: { phone: phone.trim() } })
      setNotice(res.message)
      setStep('code')
      setCooldown(60)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function resetPassword(e) {
    e.preventDefault()
    setError(''); setNotice(''); setFieldError('')
    if (password !== confirm) {
      setFieldError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await api('/auth/reset', { method: 'POST', body: { phone: phone.trim(), otp: otp.trim(), newPassword: password } })
      navigate('/login', { state: { notice: 'Password changed. Sign in with your new password.' } })
    } catch (err) {
      if (err.fields?.password) setFieldError(err.fields.password)
      else setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout
      title="Reset password"
      subtitle={step === 'phone' ? 'We will text a 6-digit code to your registered mobile number.' : 'Enter the code and choose a new password.'}
    >
      {notice && <p className="notice" role="status">{notice}</p>}

      {step === 'phone' ? (
        <form onSubmit={sendCode}>
          <label>Mobile number (with country code)
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder="+919876543210" autoComplete="tel" required />
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          <button disabled={busy}>{busy ? 'Sending…' : 'Send code'}</button>
        </form>
      ) : (
        <form onSubmit={resetPassword}>
          <label>6-digit code
            <input value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric"
              pattern="\d{6}" maxLength={6} autoComplete="one-time-code" required />
          </label>
          <label>New password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password" aria-invalid={!!fieldError} required />
          </label>
          <label>Confirm new password
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password" required />
            {fieldError && <span className="error">{fieldError}</span>}
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          <button disabled={busy}>{busy ? 'Saving…' : 'Change password'}</button>
          <button type="button" className="ghost" onClick={sendCode} disabled={busy || cooldown > 0}>
            {cooldown > 0 ? `Send a new code in ${cooldown}s` : 'Send a new code'}
          </button>
        </form>
      )}

      <p className="links">
        <Link to="/login">Back to sign in</Link>
        {step === 'code' && (
          <a href="#change" onClick={(e) => { e.preventDefault(); setStep('phone'); setError(''); setNotice('') }}>
            Use a different number
          </a>
        )}
      </p>
    </AuthLayout>
  )
}
