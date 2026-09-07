import { FormEvent, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AlertCircle, LogIn, Eye, EyeOff, MailCheck, Loader2 } from 'lucide-react'
import { extractApiError } from '../utils/validation'
import client from '../services/api'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [unverified, setUnverified] = useState(false)
  const [resending, setResending] = useState(false)
  const [resendMsg, setResendMsg] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as any)?.from || '/predict'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setResendMsg(null)
    setUnverified(false)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err: any) {
      const detail = extractApiError(err)
      const isVerifyBlock = err?.response?.status === 403
      setUnverified(isVerifyBlock)
      setError(detail || (err?.message === 'Network Error' ? 'Could not reach the server. Is the backend running?' : 'Login failed. Check your email and password.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleResend = async () => {
    setResending(true)
    setResendMsg(null)
    try {
      const { data } = await client.post('/auth/resend-verification', { email, password })
      setResendMsg(data.message + ' Don\'t forget to check your spam folder.')
    } catch (err: any) {
      setResendMsg(extractApiError(err) || 'Could not resend the email. Please try again.')
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-6 py-14">
      <div className="mb-8 text-center">
        <h1 className="font-display text-2xl font-semibold text-text-primary">Log in to PostPulse</h1>
        <p className="mt-2 text-sm text-text-secondary">Predict how your content will perform.</p>
      </div>

      {error && (
        <div className="mb-5 flex items-start gap-3 rounded-lg border border-score-low/30 bg-score-low/5 p-4 text-sm text-score-low">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {unverified && (
        <div className="mb-5 rounded-lg border border-accent/30 bg-accent/5 p-4 text-sm text-text-primary">
          <div className="flex items-start gap-3">
            <MailCheck size={18} className="mt-0.5 shrink-0 text-accent" />
            <div>
              <p className="font-medium">Email not verified yet</p>
              <p className="mt-1 text-xs text-text-secondary">
                We sent a verification link to <span className="font-medium text-text-primary">{email}</span>. Check
                your inbox, and your <strong>spam/junk folder</strong> if you don't see it.
              </p>
              <button
                type="button"
                onClick={handleResend}
                disabled={resending}
                className="focus-ring mt-3 inline-flex items-center gap-2 rounded-lg bg-vibrant-cta px-4 py-2 text-xs font-semibold text-white shadow-glow-pink transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {resending ? <Loader2 size={14} className="animate-spin" /> : <MailCheck size={14} />}
                Resend verification email
              </button>
              {resendMsg && <p className="mt-2 text-xs text-text-secondary">{resendMsg}</p>}
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Email</span>
          <input
            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-text-primary focus-ring focus:border-accent/50"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Password</span>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'} required value={password} onChange={(e) => setPassword(e.target.value)}
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
        </label>
        <button
          type="submit" disabled={submitting}
          className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg bg-vibrant-cta py-3 font-display font-semibold text-white shadow-glow-pink transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <LogIn size={17} />
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-text-secondary">
        Don't have an account?{' '}
        <Link to="/register" className="font-medium text-accent hover:underline">Sign up</Link>
      </p>
    </div>
  )
}

