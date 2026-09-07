export type Strength = 'none' | 'weak' | 'medium' | 'strong'

export interface StrengthResult {
  level: Strength
  score: number
  max: number
  label: string
  checks: { label: string; ok: boolean }[]
}

export function assessPassword(pw: string): StrengthResult {
  const checks = [
    { label: '8+ characters', ok: pw.length >= 8 },
    { label: 'Lowercase letter', ok: /[a-z]/.test(pw) },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(pw) },
    { label: 'Number', ok: /\d/.test(pw) },
    { label: 'Special character', ok: /[^A-Za-z0-9]/.test(pw) },
  ]
  const score = checks.filter((c) => c.ok).length
  let level: Strength = 'none'
  if (pw.length === 0) level = 'none'
  else if (score <= 2) level = 'weak'
  else if (score <= 4) level = 'medium'
  else level = 'strong'

  const label = level === 'none' ? '' : level === 'weak' ? 'Weak' : level === 'medium' ? 'Medium' : 'Strong'
  return { level, score, max: checks.length, label, checks }
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function isValidEmail(email: string): boolean {
  return EMAIL_RE.test(email.trim())
}

export function extractApiError(err: any): string | null {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (first && typeof first.msg === 'string') return first.msg
  }
  return err?.response?.data?.message || null
}
