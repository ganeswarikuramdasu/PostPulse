import { useEffect, useState } from 'react'

interface ScoreGaugeProps {
  score: number // 0-100
  size?: number
  label?: string
  animate?: boolean
}

function colorForScore(score: number) {
  if (score >= 85) return '#34D399' // Excellent
  if (score >= 70) return '#2DD4BF' // Good
  if (score >= 40) return '#FBBF24' // Moderate
  return '#FB7185' // Low
}

function categoryForScore(score: number) {
  if (score >= 85) return 'Excellent'
  if (score >= 70) return 'Good'
  if (score >= 40) return 'Moderate'
  return 'Low'
}

export default function ScoreGauge({ score, size = 220, label, animate = true }: ScoreGaugeProps) {
  const [displayScore, setDisplayScore] = useState(animate ? 0 : score)

  useEffect(() => {
    if (!animate) {
      setDisplayScore(score)
      return
    }
    const duration = 900
    const start = performance.now()
    const from = 0
    let raf: number
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplayScore(from + (score - from) * eased)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [score])

  const radius = size / 2 - 14
  const cx = size / 2
  const cy = size / 2
  const startAngle = 180
  const endAngle = 0
  const sweep = (displayScore / 100) * 180

  const polarToCartesian = (angleDeg: number) => {
    const angle = (Math.PI / 180) * angleDeg
    return { x: cx + radius * Math.cos(angle), y: cy - radius * Math.sin(angle) }
  }

  const trackStart = polarToCartesian(startAngle)
  const trackEnd = polarToCartesian(endAngle)
  const valueEnd = polarToCartesian(startAngle - sweep)
  const largeArc = sweep > 180 ? 1 : 0

  const color = colorForScore(score)

  return (
    <div className="flex flex-col items-center" role="img" aria-label={`Performance score ${Math.round(score)} out of 100`}>
      <svg width={size} height={size / 2 + 24} viewBox={`0 0 ${size} ${size / 2 + 24}`}>
        <path
          d={`M ${trackStart.x} ${trackStart.y} A ${radius} ${radius} 0 0 1 ${trackEnd.x} ${trackEnd.y}`}
          fill="none"
          stroke="#1A2233"
          strokeWidth={14}
          strokeLinecap="round"
        />
        <path
          d={`M ${trackStart.x} ${trackStart.y} A ${radius} ${radius} 0 ${largeArc} 1 ${valueEnd.x} ${valueEnd.y}`}
          fill="none"
          stroke={color}
          strokeWidth={14}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 8px ${color}55)` }}
        />
        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          className="font-mono"
          fontSize={size * 0.2}
          fontWeight={600}
          fill="#EDF1F7"
        >
          {Math.round(displayScore)}
        </text>
        <text x={cx} y={cy + 16} textAnchor="middle" className="font-mono" fontSize={12} fill="#8891A5">
          / 100
        </text>
      </svg>
      <div className="mt-1 flex items-center gap-2">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-display text-sm font-medium" style={{ color }}>
          {categoryForScore(score)}
        </span>
        {label && <span className="text-xs text-text-muted">· {label}</span>}
      </div>
    </div>
  )
}
