import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchHistory, fetchPredictionDetail } from '../services/api'
import type { HistoryItem } from '../types'
import { LoadingState, EmptyState, ErrorState } from '../components/States'
import { X } from 'lucide-react'

const categoryColor: Record<string, string> = {
  Excellent: 'text-score-high bg-score-high/10',
  Good: 'text-accent-teal bg-accent-teal/10',
  Moderate: 'text-score-medium bg-score-medium/10',
  Low: 'text-score-low bg-score-low/10',
}

export default function History() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<any | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const load = () => {
    setLoading(true)
    setError(null)
    fetchHistory()
      .then((res) => setItems(res.items))
      .catch(() => setError('Could not load prediction history. Make sure the backend is running and VITE_API_URL is set correctly.'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openDetail = async (id: number) => {
    setDetailLoading(true)
    try {
      const data = await fetchPredictionDetail(id)
      setDetail(data)
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Prediction History</h1>
      <p className="mt-2 text-text-secondary">Every prediction you've run, pulled from the database.</p>

      <div className="mt-8">
        {loading && <LoadingState label="Loading history…" />}
        {!loading && error && <ErrorState message={error} onRetry={load} />}
        {!loading && !error && items.length === 0 && (
          <EmptyState
            title="No predictions yet"
            description="Once you run a prediction, it'll show up here with its score, category, and forecasted metrics."
            action={
              <Link to="/predict" className="focus-ring mt-2 rounded-lg bg-vibrant-cta px-5 py-2.5 text-sm font-semibold text-white shadow-glow-pink">
                Make your first prediction
              </Link>
            }
          />
        )}
        {!loading && !error && items.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-wider text-text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Format</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Predicted views</th>
                  <th className="px-4 py-3 font-medium">Performance</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => openDetail(item.id)}
                    className="cursor-pointer border-t border-border bg-bg transition-colors hover:bg-surface-hover"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-text-primary">{item.content_type}</td>
                    <td className="px-4 py-3 text-text-secondary">{item.creator_category}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-text-primary">{item.performance_score.toFixed(1)}</td>
                    <td className="px-4 py-3 font-mono text-text-secondary">{item.expected_views.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${categoryColor[item.performance_category] || ''}`}>
                        {item.performance_category}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6" onClick={() => setDetail(null)}>
          <div
            className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-surface p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-display text-lg font-semibold text-text-primary">Prediction #{detail.id}</h3>
              <button onClick={() => setDetail(null)} className="focus-ring rounded-md p-1 text-text-muted hover:text-text-primary">
                <X size={18} />
              </button>
            </div>
            <pre className="whitespace-pre-wrap break-words rounded-lg bg-surface-raised p-4 font-mono text-xs text-text-secondary">
              {JSON.stringify(detail.result, null, 2)}
            </pre>
          </div>
        </div>
      )}
      {detailLoading && <LoadingState label="Loading prediction…" />}
    </div>
  )
}
