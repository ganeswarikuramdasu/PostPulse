import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AlertCircle, CheckCircle2, UserPlus } from 'lucide-react'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const { register } = useAuth()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setMessage(null)
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setSubmitting(true)
    try {
      const msg = await register(email, password)
      setMessage(msg)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed.')
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
        <p className="mt-4 text-xs text-text-muted">
          Running locally without email configured? The verification link was printed to your
          backend terminal instead.
        </p>
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

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Email</span>
          <input
            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-text-primary focus-ring focus:border-accent/50"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-text-primary">Password</span>
          <input
            type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-text-primary focus-ring focus:border-accent/50"
          />
          <span className="mt-1 block text-xs text-text-muted">At least 8 characters.</span>
        </label>
        <button
          type="submit" disabled={submitting}
          className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg bg-accent py-3 font-display font-semibold text-bg shadow-glow transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-60"
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
