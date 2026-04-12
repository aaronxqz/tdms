/**
 * AssignModal.jsx
 *
 * A simple modal dialog that collects assigned_date and start_time
 * before calling the assign endpoint. Appears when user clicks "Assign"
 * on a TaskChunkCard.
 */

import { useState } from 'react'
import { assignTaskChunk } from '../services/api'

export default function AssignModal({ chunk, onClose, onSuccess }) {
  const [date, setDate] = useState('')
  const [time, setTime] = useState('09:00')
  const [note, setNote] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!date) { setError('Please select an assigned date.'); return }
    setLoading(true)
    setError(null)
    try {
      const assigned = await assignTaskChunk(chunk.chunk_id, {
        assigned_date: new Date(`${date}T${time}:00`).toISOString(),
        start_time: time,
        note: note || undefined,
      })
      onSuccess(assigned)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to assign task chunk.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: '#000a',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }}>
      <div className="card" style={{ width: 420, maxWidth: '92vw' }}>
        <h3 style={{ marginBottom: 16 }}>Assign Task Chunk</h3>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
          {chunk.chunk_id} — {chunk.content.slice(0, 60)}…
        </p>

        {error && <div className="error-msg">{error}</div>}

        <label style={{ display: 'block', marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Assigned Date *
          </span>
          <input type="date" value={date} onChange={e => setDate(e.target.value)} />
        </label>

        <label style={{ display: 'block', marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Start Time
          </span>
          <input type="time" value={time} onChange={e => setTime(e.target.value)} />
        </label>

        <label style={{ display: 'block', marginBottom: 20 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Note (optional)
          </span>
          <textarea
            rows={2}
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="Any notes about this assignment…"
          />
        </label>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Assigning…' : 'Confirm Assignment'}
          </button>
        </div>
      </div>
    </div>
  )
}
