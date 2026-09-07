import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ACCOUNT_TYPES, CREATOR_CATEGORIES, CONTENT_TYPES, DAYS, type ContentInput } from '../types'
import { predictContent } from '../services/api'
import { extractApiError } from '../utils/validation'
import { AlertCircle } from 'lucide-react'

const initialForm: ContentInput = {
  content_type: 'reel',
  creator_category: 'Technology',
  account_type: 'creator',
  has_call_to_action: 1,
  description_length: 120,
  hashtags: 8,
  followers: 25000,
  account_age_months: 6,
  historical_avg_views: 5000,
  historical_engagement_rate: 4.2,
  posting_hour: 19,
  day_of_week: 'Saturday',
}

type Errors = Partial<Record<keyof ContentInput, string>>

function Field({
  label, hint, children,
}: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-text-primary">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-text-muted">{hint}</span>}
    </label>
  )
}

const inputClass =
  'w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-text-primary focus-ring focus:border-accent/50 placeholder:text-text-muted'

export default function Predict() {
  const [form, setForm] = useState<ContentInput>(initialForm)
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const navigate = useNavigate()

  const update = <K extends keyof ContentInput>(key: K, value: ContentInput[K]) => {
    setForm((f) => ({ ...f, [key]: value }))
    setErrors((e) => ({ ...e, [key]: undefined }))
  }

  const validate = (): boolean => {
    const e: Errors = {}
    if (form.description_length < 0 || form.description_length > 5000) e.description_length = 'Must be between 0 and 5000'
    if (form.hashtags < 0 || form.hashtags > 50) e.hashtags = 'Must be between 0 and 50'
    if (form.followers < 0) e.followers = 'Cannot be negative'
    if (form.followers > 500_000_000) e.followers = 'Must be 500M or less'
    if (form.account_age_months < 0 || form.account_age_months > 300) e.account_age_months = 'Must be between 0 and 300 months'
    if (form.historical_avg_views < 0) e.historical_avg_views = 'Cannot be negative'
    if (form.historical_engagement_rate < 0 || form.historical_engagement_rate > 100) e.historical_engagement_rate = 'Must be a percentage 0–100'
    if (form.posting_hour < 0 || form.posting_hour > 23) e.posting_hour = 'Must be 0–23'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (ev: FormEvent) => {
    ev.preventDefault()
    setApiError(null)
    if (!validate()) return
    setSubmitting(true)
    try {
      const result = await predictContent(form)
      navigate('/results', { state: { result, input: form } })
    } catch (err: any) {
      setApiError(
        extractApiError(err) || 'Could not reach the prediction API. Make sure the backend is running and VITE_API_URL is set correctly.'
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Predict Performance</h1>
      <p className="mt-2 text-text-secondary">
        Fill in your Instagram post and account details.
      </p>

      {apiError && (
        <div className="mt-6 flex items-start gap-3 rounded-lg border border-score-low/30 bg-score-low/5 p-4 text-sm text-score-low">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span>{apiError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-8 space-y-10">
        <fieldset>
          <legend className="mb-4 font-display text-sm font-semibold uppercase tracking-widest text-text-muted">
            Content
          </legend>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Content format">
              <select className={inputClass} value={form.content_type} onChange={(e) => update('content_type', e.target.value)}>
                {CONTENT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Creator / niche category">
              <select className={inputClass} value={form.creator_category} onChange={(e) => update('creator_category', e.target.value)}>
                {CREATOR_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Caption length (characters)" hint={errors.description_length}>
              <input type="number" className={inputClass} value={form.description_length}
                onChange={(e) => update('description_length', Number(e.target.value))} />
            </Field>
            <Field label="Hashtags" hint={errors.hashtags}>
              <input type="number" className={inputClass} value={form.hashtags}
                onChange={(e) => update('hashtags', Number(e.target.value))} />
            </Field>
            <Field label="Includes a call-to-action?">
              <select className={inputClass} value={form.has_call_to_action}
                onChange={(e) => update('has_call_to_action', Number(e.target.value))}>
                <option value={1}>Yes</option>
                <option value={0}>No</option>
              </select>
            </Field>
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-4 font-display text-sm font-semibold uppercase tracking-widest text-text-muted">
            Account
          </legend>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Account type">
              <select className={inputClass} value={form.account_type} onChange={(e) => update('account_type', e.target.value)}>
                {ACCOUNT_TYPES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Followers" hint={errors.followers}>
              <input type="number" className={inputClass} value={form.followers}
                onChange={(e) => update('followers', Number(e.target.value))} />
            </Field>
            <Field label="Account age (months)" hint={errors.account_age_months}>
              <input type="number" step="0.1" className={inputClass} value={form.account_age_months}
                onChange={(e) => update('account_age_months', Number(e.target.value))} />
            </Field>
            <Field label="Historical average reach" hint={errors.historical_avg_views}>
              <input type="number" className={inputClass} value={form.historical_avg_views}
                onChange={(e) => update('historical_avg_views', Number(e.target.value))} />
            </Field>
            <Field label="Historical engagement rate (%)" hint={errors.historical_engagement_rate}>
              <input type="number" step="0.1" className={inputClass} value={form.historical_engagement_rate}
                onChange={(e) => update('historical_engagement_rate', Number(e.target.value))} />
            </Field>
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-4 font-display text-sm font-semibold uppercase tracking-widest text-text-muted">
            Publishing
          </legend>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Posting hour (0–23)" hint={errors.posting_hour}>
              <input type="number" min={0} max={23} className={inputClass} value={form.posting_hour}
                onChange={(e) => update('posting_hour', Number(e.target.value))} />
            </Field>
            <Field label="Day of week">
              <select className={inputClass} value={form.day_of_week} onChange={(e) => update('day_of_week', e.target.value)}>
                {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </Field>
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={submitting}
          className="focus-ring w-full rounded-lg bg-vibrant-cta py-3.5 font-display font-semibold text-white shadow-glow-pink transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? 'Running prediction…' : 'Predict Performance'}
        </button>
      </form>
    </div>
  )
}
