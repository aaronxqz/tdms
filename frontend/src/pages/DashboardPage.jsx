/**
 * pages/DashboardPage.jsx
 *
 * The home screen. Shows system-wide counters and a quick overview.
 * This is the first page a developer should get working — if the
 * numbers appear, the API connection is confirmed healthy.
 */

import { useEffect, useState } from 'react'
import { getDashboard } from '../services/api'

function StatCard({ label, value, color }) {
  return (
    <div className="card" style={{ textAlign: 'center', minWidth: 140 }}>
      <div style={{ fontSize: 36, fontWeight: 700, color: color || 'var(--text)' }}>
        {value ?? '—'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{label}</div>
    </div>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDashboard()
      .then(setStats)
      .catch(() => setError('Could not load dashboard. Is the backend running?'))
  }, [])

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Dashboard</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 28 }}>
        System-wide task chunk summary
      </p>

      {error && <div className="error-msg">{error}</div>}

      {stats && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <StatCard label="Waiting" value={stats.waiting} color="var(--urgency-4)" />
          <StatCard label="In Progress" value={stats.in_progress} color="var(--status-in-progress)" />
          <StatCard label="Completed" value={stats.completed} color="var(--status-completed)" />
          <StatCard label="Failed" value={stats.failed} color="var(--status-failed)" />
          <StatCard label="Breached" value={stats.breached} color="var(--urgency-1)" />
          <StatCard
            label="Avg Wait (hrs)"
            value={stats.avg_waiting_hours ?? 'N/A'}
            color="var(--text-muted)"
          />
        </div>
      )}

      {!stats && !error && (
        <p style={{ color: 'var(--text-muted)' }}>Loading…</p>
      )}
    </div>
  )
}
