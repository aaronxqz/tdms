import { URGENCY_COLORS } from '../utils/urgency'

export default function UrgencyBadge({ label }) {
  const color = URGENCY_COLORS[label] || '#888'
  return (
    <span
      className="label"
      style={{ background: color + '22', color, border: `1px solid ${color}55` }}
    >
      {label}
    </span>
  )
}
