import type { ImportantFactor } from '../types'

export default function FactorBars({ factors }: { factors: ImportantFactor[] }) {
  const maxImportance = Math.max(...factors.map((f) => f.importance), 1)
  return (
    <div className="space-y-4">
      {factors.map((factor, i) => (
        <div key={i}>
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="text-sm font-medium text-text-primary">{factor.feature}</span>
            <span className="font-mono text-xs text-text-secondary">{factor.importance.toFixed(1)}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-raised">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent-orange via-accent-pink to-accent-violet transition-all duration-700"
              style={{ width: `${(factor.importance / maxImportance) * 100}%` }}
            />
          </div>
          <p className="mt-1.5 text-xs text-text-muted">{factor.description}</p>
        </div>
      ))}
    </div>
  )
}
