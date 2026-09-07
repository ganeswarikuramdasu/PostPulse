import { Link, useLocation, useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import { Eye, Heart, Gauge, Lightbulb, Target, ListChecks, RotateCcw } from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'
import MetricCard from '../components/MetricCard'
import FactorBars from '../components/FactorBars'
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
            <Link to="/predict" className="focus-ring mt-2 rounded-lg bg-vibrant-cta px-5 py-2.5 text-sm font-semibold text-white shadow-glow-pink">
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
            accent="#FFC531"
            sublabel={`Model: ${result.model_category_prediction}`}
          />

          <div className="col-span-full rounded-xl border border-border bg-surface p-5">
            <h3 className="mb-4 font-display text-sm font-semibold text-text-primary">Category probability breakdown</h3>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={probData} layout="vertical" margin={{ left: 8, right: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#4A2B78" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8B7BB8', fontSize: 12 }} unit="%" />
                <YAxis type="category" dataKey="category" tick={{ fill: '#FDF4FF', fontSize: 13 }} width={70} />
                <Tooltip
                  contentStyle={{ background: '#221240', border: '1px solid #4A2B78', borderRadius: 8, fontSize: 13 }}
                  formatter={(v: number) => [`${v}%`, 'Probability']}
                />
                <Bar dataKey="probability" fill="#FF6B4A" radius={[0, 6, 6, 0]} barSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Important factors */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-6">
          <h3 className="mb-5 font-display text-lg font-semibold text-text-primary">Important factors</h3>
          {result.important_factors.length > 0 ? (
            <FactorBars factors={result.important_factors} />
          ) : (
            <p className="text-sm text-text-secondary">
              No factor had a measurable effect on this prediction. The model's output
              doesn't meaningfully depend on any input feature for this dataset.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-6">
          <div className="mb-5 flex items-center gap-2">
            <Lightbulb size={18} className="text-accent" />
            <h3 className="font-display text-lg font-semibold text-text-primary">How to read this</h3>
          </div>
          <ul className="space-y-3 text-sm text-text-secondary">
            <li className="flex gap-3">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span>
                <strong className="text-text-primary">Predictions</strong> forecast reach and engagement from your
                inputs, not guarantees.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span>
                <strong className="text-text-primary">Important factors</strong> show which inputs drive this
                prediction the most.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span>
                <strong className="text-text-primary">Change one variable</strong> at a time and re-run to see how the
                forecast responds - that's how you find your biggest reach lever.
              </span>
            </li>
          </ul>
        </div>
      </div>

      {/* Suggestions to increase views */}
      {result.recommendations.length > 0 && (
        <div className="mt-6 rounded-2xl border border-accent/25 bg-gradient-to-br from-surface to-surface-raised p-6 shadow-glow-violet">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-vibrant-cta text-white">
              <Target size={20} />
            </div>
            <div>
              <h2 className="font-display text-xl font-semibold text-text-primary">Boost your views</h2>
              <p className="text-xs text-text-secondary">
                Actionable suggestions tailored to your inputs to help raise reach and engagement.
              </p>
            </div>
          </div>

          <ol className="mt-6 grid gap-3">
            {result.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-3 rounded-lg border border-border bg-surface bg-opacity-60 p-4">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-pink font-mono text-xs font-bold text-white">
                  {i + 1}
                </span>
                <span className="text-sm leading-relaxed text-text-secondary">{rec}</span>
              </li>
            ))}
          </ol>

          <p className="mt-4 flex items-center gap-2 text-xs text-text-muted">
            <ListChecks size={13} />
            Tweak the ones you can (posting time, hashtags, CTA, caption) and re-run the prediction to compare.
          </p>
        </div>
      )}
    </div>
  )
}
