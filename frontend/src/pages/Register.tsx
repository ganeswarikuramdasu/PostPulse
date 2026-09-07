import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AlertCircle, CheckCircle2, UserPlus, Eye, EyeOff, Check, X } from 'lucide-react'
import { assessPassword, isValidEmail, extractApiError } from '../utils/validation'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [touched, setTouched] = useState({ email: false, password: false })
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const { register } = useAuth()

  const strength = assessPassword(password)
  const emailValid = isValidEmail(email)
  const emailError = touched.email && !emailValid ? 'Please enter a valid email address.' : null
  const confirmError = confirm.length > 0 && confirm !== password ? 'Passwords do not match.' : null

  const strengthColor =
    strength.level === 'weak' ? 'bg-score-low' : strength.level === 'medium' ? 'bg-accent-pink' : 'bg-score-high'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setMessage(null)

    if (!emailValid) {
      setTouched((t) => ({ ...t, email: true }))
      setError('Please enter a valid email address.')
      return
    }
    if (strength.level !== 'strong') {
      setTouched((t) => ({ ...t, password: true }))
      setError('Please choose a stronger password — use uppercase, numbers, and a special character.')
      return
    }
    if (confirm !== password) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      const msg = await register(email, password)
      setMessage(msg)
    } catch (err: any) {
      const timedOut = err?.code === 'ECONNABORTED'
      const detail = extractApiError(err)
      if (timedOut) {
        setError('The request took too long. Your account may already have been created - please check your inbox (and spam) for the verification link before trying again.')
      } else {
        setError(detail || (err?.message === 'Network Error' ? 'Could not reach the server. Is the backend running?' : 'Registration failed. Please try again.'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (message) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-6 py-14 text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-score-high/10 text-score-high">
          <CheckCircle2 size={24} />
        </div>
        <h1 className="font-display text-xl font-semibold text-text-primary">Check your inbox</h1>
        <p className="mt-2 text-sm text-text-secondary">{message}</p>
        <div className="mt-4 rounded-lg border border-border bg-surface/50 p-3 text-left text-xs text-text-secondary">
          <p>
            We sent the verification link to your email. If you don't see it in your inbox within a few minutes,
            please also check your <strong className="text-text-primary">spam</strong> or{' '}
            <strong className="text-text-primary">junk</strong> folder.
          </p>
        </div>
        <Link to="/login" className="focus-ring mt-6 rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-text-primary hover:border-accent/40">
          Go to login
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-6 py-14">
      <div className="mb-8 text-center">
        <h1 className="font-display text-2xl font-semibold text-text-primary">Create your PostPulse account</h1>
        <p className="mt-2 text-sm text-text-secondary">Free to start. Verify your email to unlock predictions.</p>
      </div>

      {error && (
        <div className="mb-5 flex items-start gap-3 rounded-lg border border-score-low/30 bg-score-low/5 p-4 text-sm text-score-low">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => { setEmail(e.target.value); setTouched((t) => ({ ...t, email: true })) }}
            placeholder="you@example.com"
            className={`w-full rounded-lg border px-3.5 py-2.5 text-sm text-text-primary focus-ring focus:border-accent/50 bg-surface ${
              emailError ? 'border-score-low/60' : emailValid && email ? 'border-score-high/50' : 'border-border'
            }`}
          />
          {emailError ? (
            <span className="mt-1 flex items-center gap-1 text-xs text-score-low">
              <AlertCircle size={12} /> {emailError}
            </span>
          ) : emailValid && email ? (
            <span className="mt-1 flex items-center gap-1 text-xs text-score-high">
              <Check size={12} /> Looks good
            </span>
          ) : (
            <span className="mt-1 block text-xs text-text-muted">e.g. name@example.com</span>
          )}
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Password</span>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              required
              minLength={8}
              value={password}
              onChange={(e) => { setPassword(e.target.value); setTouched((t) => ({ ...t, password: true })) }}
              placeholder="Enter a strong password"
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 pr-11 text-sm text-text-primary focus-ring focus:border-accent/50"
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-text-muted transition-colors hover:text-accent"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          {password.length > 0 && (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <div className="flex h-1.5 flex-1 gap-1">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className={`h-full flex-1 rounded-full transition-colors ${
                        strength.level === 'none' ? 'bg-border' : i <= strength.score ? strengthColor : 'bg-border'
                      }`}
                    />
                  ))}
                </div>
                <span
                  className={`text-xs font-medium ${
                    strength.level === 'weak' ? 'text-score-low' : strength.level === 'medium' ? 'text-accent-pink' : strength.level === 'strong' ? 'text-score-high' : 'text-text-muted'
                  }`}
                >
                  {strength.label}
                </span>
              </div>
              <ul className="mt-2 grid grid-cols-1 gap-1 text-xs">
                {strength.checks.map((c) => (
                  <li key={c.label} className={`flex items-center gap-1.5 ${c.ok ? 'text-score-high' : 'text-text-muted'}`}>
                    {c.ok ? <Check size={12} /> : <X size={12} />} {c.label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Confirm password</span>
          <div className="relative">
            <input
              type={showConfirm ? 'text' : 'password'}
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Re-enter your password"
              className={`w-full rounded-lg border bg-surface px-3.5 py-2.5 pr-11 text-sm text-text-primary focus-ring focus:border-accent/50 ${
                confirmError ? 'border-score-low/60' : 'border-border'
              }`}
            />
            <button
              type="button"
              onClick={() => setShowConfirm((s) => !s)}
              aria-label={showConfirm ? 'Hide password' : 'Show password'}
              className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-text-muted transition-colors hover:text-accent"
            >
              {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {confirmError && (
            <span className="mt-1 flex items-center gap-1 text-xs text-score-low">
              <AlertCircle size={12} /> Passwords do not match.
            </span>
          )}
        </label>

        <button
          type="submit" disabled={submitting}
          className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg bg-vibrant-cta py-3 font-display font-semibold text-white shadow-glow-pink transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <UserPlus size={17} />
          {submitting ? 'Creating account…' : 'Sign up'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-text-secondary">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent hover:underline">Log in</Link>
      </p>
    </div>
  )
}
