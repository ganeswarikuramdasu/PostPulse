export default function Footer() {
  return (
    <footer className="border-t border-border py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-text-muted sm:flex-row">
        <p>PostPulse — Content Performance Predictor. A portfolio ML project.</p>
        <p className="font-mono text-xs">Predictions are model estimates, not guarantees.</p>
      </div>
    </footer>
  )
}
