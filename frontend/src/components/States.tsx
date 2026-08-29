import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'
import { ReactNode } from 'react'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-text-secondary">
      <Loader2 className="animate-spin text-accent" size={28} />
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-20 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-raised text-text-muted">
        <Inbox size={22} />
      </div>
      <h3 className="font-display text-lg font-medium text-text-primary">{title}</h3>
      <p className="max-w-sm text-sm text-text-secondary">{description}</p>
      {action}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-score-low/30 bg-score-low/5 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-score-low/10 text-score-low">
        <AlertTriangle size={22} />
      </div>
      <h3 className="font-display text-lg font-medium text-text-primary">Something went wrong</h3>
      <p className="max-w-sm text-sm text-text-secondary">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="focus-ring mt-2 rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:border-accent/40"
        >
          Try again
        </button>
      )}
    </div>
  )
}
