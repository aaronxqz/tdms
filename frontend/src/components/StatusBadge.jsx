import { STATUS_COLORS, STATUS_LABELS } from '../utils/urgency'

export default function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || '#888'
  const label = STATUS_LABELS[status] || status
  return (
    <span
      className="label"
      style={{ background: color + '22', color, border: `1px solid ${color}55` }}
    >
      {label}
    </span>
  )
}
