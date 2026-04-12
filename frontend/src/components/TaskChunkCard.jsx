/**
 * TaskChunkCard.jsx
 *
 * Reusable card displayed in both the Waiting and Assigned lists.
 * Receives the chunk data and action callbacks from the parent page.
 * The card itself doesn't call the API — it raises events upward.
 * This is the "dumb component" pattern: display only, no side effects.
 */

import UrgencyBadge from './UrgencyBadge'
import StatusBadge from './StatusBadge'
import { formatTimeRange } from '../utils/urgency'

export default function TaskChunkCard({ chunk, onAssign, onAck, onComplete, onFail }) {
  const isBreached = chunk.status === 'BREACH' || chunk.status === 'BREACH_ACTION'
  const isInProgress = chunk.status === 'IN_PROGRESS'

  return (
    <div
      className="card"
      style={{
        marginBottom: 12,
        borderLeft: isBreached
          ? '3px solid var(--urgency-1)'
          : isInProgress
          ? '3px solid var(--urgency-4)'
          : '3px solid var(--border)',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>
          {chunk.chunk_id}
        </span>
        <UrgencyBadge label={chunk.urgency_label} />
        <StatusBadge status={chunk.status} />
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 12 }}>
          ⏱ {formatTimeRange(chunk.time_period, chunk.time_divergent)}
        </span>
      </div>

      {/* Content */}
      <p style={{ fontSize: 14, lineHeight: 1.5, marginBottom: 8 }}>{chunk.content}</p>

      {/* Goal & reference */}
      {chunk.goal_id && (
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
          Goal: <strong>{chunk.goal_id}</strong>
        </p>
      )}
      {chunk.reference_link && (
        <p style={{ fontSize: 12, marginBottom: 8 }}>
          <a href={chunk.reference_link} target="_blank" rel="noreferrer">
            📎 Reference
          </a>
        </p>
      )}

      {/* Breach warning banner */}
      {isBreached && (
        <div style={{
          background: '#3f1515',
          border: '1px solid #7f2020',
          borderRadius: 6,
          padding: '8px 12px',
          fontSize: 12,
          color: '#fca5a5',
          marginBottom: 10,
        }}>
          ⚠️ This task chunk has exceeded its wait window.
          Acknowledge to reduce urgency by one level.
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {(chunk.status === 'OK' || isBreached) && onAssign && (
          <button className="btn-primary" onClick={() => onAssign(chunk)}>
            Assign
          </button>
        )}
        {isBreached && onAck && (
          <button className="btn-ghost" onClick={() => onAck(chunk.chunk_id)}>
            I Acknowledge — Reduce Urgency
          </button>
        )}
        {isInProgress && onComplete && (
          <button
            className="btn-primary"
            style={{ background: 'var(--status-completed)' }}
            onClick={() => onComplete(chunk.chunk_id)}
          >
            Mark Complete
          </button>
        )}
        {isInProgress && onFail && (
          <button className="btn-danger" onClick={() => onFail(chunk.chunk_id)}>
            Mark Failed
          </button>
        )}
      </div>
    </div>
  )
}
