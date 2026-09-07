import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail } from '../services/api'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { extractApiError } from '../utils/validation'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const fired = useRef(false)

  useEffect(() => {
    if (fired.current) return
    if (!token) {
      setStatus('error')
      setMessage('No verification token found in the link.')
      fired.current = true
      return
    }
    fired.current = true
    verifyEmail(token)
      .then((data) => {
        setStatus('success')
        setMessage(data.message)
      })
      .catch((err) => {
        setStatus('error')
        setMessage(extractApiError(err) || 'Verification failed. Please try the login page or check your email for a fresh link.')
      })
  }, [token])

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center px-6 py-14 text-center">
      {status === 'loading' && (
        <>
          <Loader2 size={32} className="animate-spin text-accent" />
          <p className="mt-4 text-sm text-text-secondary">Verifying your email…</p>
        </>
      )}
      {status === 'success' && (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-score-high/10 text-score-high">
            <CheckCircle2 size={24} />
          </div>
          <h1 className="mt-4 font-display text-xl font-semibold text-text-primary">Email verified</h1>
          <p className="mt-2 text-sm text-text-secondary">{message}</p>
          <Link to="/login" className="focus-ring mt-6 rounded-lg bg-vibrant-cta px-5 py-2.5 text-sm font-semibold text-white shadow-glow-pink">
            Log in
          </Link>
        </>
      )}
      {status === 'error' && (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-score-low/10 text-score-low">
            <XCircle size={24} />
          </div>
          <h1 className="mt-4 font-display text-xl font-semibold text-text-primary">Verification failed</h1>
          <p className="mt-2 text-sm text-text-secondary">{message}</p>
          <Link to="/login" className="focus-ring mt-6 rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-text-primary hover:border-accent/40">
            Back to login
          </Link>
        </>
      )}
    </div>
  )
}
