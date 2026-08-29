import { ShieldAlert } from 'lucide-react'

export default function DataQualityBanner({ notice }: { notice?: string | null }) {
  if (!notice) return null
  return (
    <div className="flex items-start gap-3 rounded-lg border border-score-medium/30 bg-score-medium/5 p-4 text-sm text-text-secondary">
      <ShieldAlert size={18} className="mt-0.5 shrink-0 text-score-medium" />
      <div>
        <p className="font-medium text-text-primary">This model has no real predictive signal</p>
        <p className="mt-1">{notice}</p>
      </div>
    </div>
  )
}
