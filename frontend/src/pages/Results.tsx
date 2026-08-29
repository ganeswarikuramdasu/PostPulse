import { Link, useLocation, useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import { Eye, Heart, Gauge, Lightbulb, RotateCcw } from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'
import MetricCard from '../components/MetricCard'
import FactorBars from '../components/FactorBars'
import DataQualityBanner from '../components/DataQualityBanner'
import { EmptyState } from '../components/States'
import type { ContentInput, PredictionResponse } from '../types'

export default function Results() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state as { result: PredictionResponse; input: ContentInput } | null

  if (!state) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14">
        <EmptyState
          title="No prediction to show"
          description="Run a prediction first and we'll bring you straight here with your results."
          action={
            <Link to="/predict" className="focus-ring mt-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-bg">
              Make a prediction
            </Link>
          }
        />
      </div>
    )
  }

  const { result, input } = state
  const probData = Object.entries(result.category_probabilities).map(([category, prob]) => ({
    category,
    probability: Math.round(prob * 1000) / 10,
  }))

  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-text-primary">Prediction Results</h1>
          <p className="mt-1 text-sm text-text-secondary">
            {input.content_type} · {input.creator_category} · posted {input.day_of_week} at {input.posting_hour}:00
          </p>
        </div>
        <button
          onClick={() => navigate('/predict')}
          className="focus-ring inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary"
        >
          <RotateCcw size={15} /> New prediction
        </button>
      </div>

      {!result.signal_detected && (
        <div className="mt-6">
          <DataQualityBanner notice={result.data_quality_notice} />
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[300px_1fr]">
        {/* Main prediction card */}
        <div className="flex flex-col items-center justify-center rounded-2xl border border-border bg-surface p-8">
          <ScoreGauge score={result.performance_score} />
          <p className="mt-4 text-center text-sm text-text-secondary">
            Model confidence: <span className="font-mono text-text-primary">{Math.round(result.confidence * 100)}%</span>
          </p>
        </div>

        {/* Metric cards */}
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            label="Expected Reach"
            value={result.expected_views.toLocaleString()}
            icon={<Eye size={16} />}
            accent="#2DD4BF"
          />
          <MetricCard
            label="Expected Engagement"
            value={`${result.expected_engagement_rate.toFixed(1)}%`}
            icon={<Heart size={16} />}
            accent="#FF6B4A"
          />
          <MetricCard
            label="Category"
            value={result.performance_category}
            icon={<Gauge size={16} />}
            accent="#FBBF24"
            sublabel={`Model: ${result.model_category_prediction}`}
          />

          <div className="col-span-full rounded-xl border border-border bg-surface p-5">
            <h3 className="mb-4 font-display text-sm font-semibold text-text-primary">Category probability breakdown</h3>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={probData} layout="vertical" margin={{ left: 8, right: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232C40" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8891A5', fontSize: 12 }} unit="%" />
                <YAxis type="category" dataKey="category" tick={{ fill: '#EDF1F7', fontSize: 13 }} width={70} />
                <Tooltip
                  contentStyle={{ background: '#121826', border: '1px solid #232C40', borderRadius: 8, fontSize: 13 }}
                  formatter={(v: number) => [`${v}%`, 'Probability']}
                />
                <Bar dataKey="probability" fill="#FF6B4A" radius={[0, 6, 6, 0]} barSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Important factors + recommendations */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-6">
          <h3 className="mb-5 font-display text-lg font-semibold text-text-primary">Important factors</h3>
          {result.important_factors.length > 0 ? (
            <FactorBars factors={result.important_factors} />
          ) : (
            <p className="text-sm text-text-secondary">
              No factor had a measurable effect on this prediction — see the notice above. The model's output
              doesn't meaningfully depend on any input feature for this dataset.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-6">
          <div className="mb-5 flex items-center gap-2">
            <Lightbulb size={18} className="text-accent" />
            <h3 className="font-display text-lg font-semibold text-text-primary">Recommendations</h3>
          </div>
          <ul className="space-y-3">
            {result.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-3 rounded-lg border border-border bg-surface-raised p-3.5 text-sm text-text-secondary">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
