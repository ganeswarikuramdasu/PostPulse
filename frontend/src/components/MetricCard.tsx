import { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: string
  icon?: ReactNode
  accent?: string
  sublabel?: string
}

export default function MetricCard({ label, value, icon, accent = '#FF6B4A', sublabel }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 transition-colors hover:border-accent/30">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text-secondary">{label}</span>
        {icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ backgroundColor: `${accent}1A`, color: accent }}>
            {icon}
          </div>
        )}
      </div>
      <p className="mt-3 font-mono text-2xl font-semibold text-text-primary">{value}</p>
      {sublabel && <p className="mt-1 text-xs text-text-muted">{sublabel}</p>}
    </div>
  )
}
