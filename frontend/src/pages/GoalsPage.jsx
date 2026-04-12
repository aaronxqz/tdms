/**
 * pages/GoalsPage.jsx
 *
 * Lists all goals and allows creating new ones.
 * Each goal card links to its associated task chunks via search.
 */

import { useEffect, useState } from 'react'
import { listGoals, createGoal } from '../services/api'
import { useNavigate } from 'react-router-dom'

export default function GoalsPage() {
  const [goals, setGoals]         = useState([])
  const [title, setTitle]         = useState('')
  const [desc, setDesc]           = useState('')
  const [error, setError]         = useState(null)
  const [formError, setFormError] = useState(null)
  const [loading, setLoading]     = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  function load() {
    setLoading(true)
    listGoals()
      .then(setGoals)
      .catch(() => setError('Failed to load goals.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function handleCreate() {
    setFormError(null)
    if (!title.trim()) { setFormError('Title is required.'); return }
    setSubmitting(true)
    try {
      await createGoal({ title: title.trim(), description: desc.trim() || undefined })
      setTitle('')
      setDesc('')
      load()
    } catch (e) {
      setFormError(e.response?.data?.detail || 'Failed to create goal.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ padding: 32, maxWidth: 860, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Goals</h1>

      {/* Create form */}
      <div className="card" style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>New Goal</h2>
        {formError && <div className="error-msg">{formError}</div>}

        <label style={{ display: 'block', marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Title *
          </span>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Complete CS344 assignments"
          />
        </label>

        <label style={{ display: 'block', marginBottom: 16 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Description (optional)
          </span>
          <textarea
            rows={2}
            value={desc}
            onChange={e => setDesc(e.target.value)}
            placeholder="What is this goal about?"
          />
        </label>

        <button className="btn-primary" onClick={handleCreate} disabled={submitting}>
          {submitting ? 'Creating…' : '+ Create Goal'}
        </button>
      </div>

      {/* Goals list */}
      {error && <div className="error-msg">{error}</div>}
      {loading && <p style={{ color: 'var(--text-muted)' }}>Loading…</p>}
      {!loading && goals.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>No goals yet. Create one above.</p>
      )}

      {goals.map(g => (
        <div key={g.goal_id} className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent)' }}>
              {g.goal_id}
            </span>
            <span style={{ fontWeight: 600, fontSize: 15 }}>{g.title}</span>
          </div>
          {g.description && (
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
              {g.description}
            </p>
          )}
          <button
            className="btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => navigate(`/search?goal_id=${g.goal_id}`)}
          >
            View task chunks →
          </button>
        </div>
      ))}
    </div>
  )
}
