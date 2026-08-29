import { Link } from 'react-router-dom'
import { ArrowRight, BarChart3, Lightbulb, Sparkles, Target, Zap, Clock } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import ScoreGauge from '../components/ScoreGauge'

const features = [
  {
    icon: <Target size={20} />,
    title: 'Performance scoring',
    description: 'A 0–100 score from a trained classifier, evaluated honestly on a held-out test set (77% accuracy, 0.92 ROC-AUC).',
  },
  {
    icon: <BarChart3 size={20} />,
    title: 'Reach & engagement forecasts',
    description: 'Separate regression models predict expected reach and expected engagement rate.',
  },
  {
    icon: <Lightbulb size={20} />,
    title: 'Explainable predictions',
    description: 'See which factors moved your score, ranked by real permutation importance from the trained model.',
  },
  {
    icon: <Zap size={20} />,
    title: 'Grounded recommendations',
    description: "Suggestions tied to the model's actual learned relationships, not generic advice.",
  },
]

const steps = [
  { title: 'Describe your post', description: 'Format, caption length, hashtags, call-to-action, posting time.' },
  { title: 'Add your account history', description: 'Followers, account age, historical reach and engagement.' },
  { title: 'Get a prediction', description: 'Score, forecasted reach, and the factors driving it.' },
]

export default function Landing() {
  const { user } = useAuth()
  const ctaLink = user ? '/predict' : '/register'
  const ctaLabel = user ? 'Predict Performance' : 'Get Started Free'

  return (
    <div>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16 sm:pt-24">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-text-secondary">
              <Sparkles size={13} className="text-accent" />
              ML-powered Instagram content analytics
            </div>
            <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight text-text-primary sm:text-5xl">
              Know how your post will land — <span className="text-accent">before</span> you publish it.
            </h1>
            <p className="mt-5 max-w-lg text-lg text-text-secondary">
              PostPulse predicts performance score, expected reach, and engagement using a trained
              ML pipeline — then tells you exactly which factors are driving the prediction.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to={ctaLink}
                className="focus-ring group inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 font-display font-semibold text-bg shadow-glow transition-transform hover:scale-[1.02]"
              >
                {ctaLabel}
                <ArrowRight size={18} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              {user && (
                <Link
                  to="/history"
                  className="focus-ring rounded-lg border border-border px-6 py-3 font-medium text-text-secondary hover:text-text-primary"
                >
                  View past predictions
                </Link>
              )}
            </div>
            <div className="mt-10 flex items-center gap-6 text-xs text-text-muted">
              <span className="font-mono">R² 0.68-0.86 on held-out data</span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="font-mono">3 model targets</span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="font-mono">Sub-second inference</span>
            </div>
          </div>

          <div className="flex justify-center">
            <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-8">
              <p className="mb-6 text-center text-xs font-medium uppercase tracking-widest text-text-muted">
                Example prediction
              </p>
              <div className="flex justify-center">
                <ScoreGauge score={84} label="Reel · Technology" />
              </div>
              <div className="mt-6 grid grid-cols-2 gap-3 border-t border-border pt-6">
                <div>
                  <p className="text-xs text-text-muted">Expected reach</p>
                  <p className="font-mono text-lg font-semibold text-text-primary">12,273</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Engagement</p>
                  <p className="font-mono text-lg font-semibold text-text-primary">5.3%</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="font-display text-2xl font-semibold text-text-primary">What you get</h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => (
            <div key={f.title} className="rounded-xl border border-border bg-surface p-5 transition-colors hover:border-accent/30">
              <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent">
                {f.icon}
              </div>
              <h3 className="font-display font-medium text-text-primary">{f.title}</h3>
              <p className="mt-2 text-sm text-text-secondary">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="font-display text-2xl font-semibold text-text-primary">How it works</h2>
        <div className="mt-8 grid gap-8 sm:grid-cols-3">
          {steps.map((s, i) => (
            <div key={s.title} className="relative">
              <span className="font-mono text-4xl font-semibold text-border">{String(i + 1).padStart(2, '0')}</span>
              <h3 className="mt-3 font-display font-medium text-text-primary">{s.title}</h3>
              <p className="mt-2 text-sm text-text-secondary">{s.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ML explanation strip */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex flex-col items-start gap-6 rounded-2xl border border-border bg-surface p-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-teal">
              <Clock size={13} /> Trained offline, served instantly
            </div>
            <h3 className="font-display text-xl font-semibold text-text-primary">
              Real models, evaluated honestly.
            </h3>
            <p className="mt-2 max-w-xl text-sm text-text-secondary">
              Every model here was selected by comparing multiple algorithms on a held-out test
              set — see the README for full model comparison tables, evaluation metrics, and an
              honest account of an earlier real-data validation that found no usable signal before
              this dataset was adopted.
            </p>
          </div>
          <Link
            to={ctaLink}
            className="focus-ring shrink-0 rounded-lg border border-accent/40 bg-accent/10 px-5 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20"
          >
            {user ? 'Try it now' : 'Sign up free'}
          </Link>
        </div>
      </section>
    </div>
  )
}
