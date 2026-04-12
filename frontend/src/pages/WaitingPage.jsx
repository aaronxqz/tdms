/**
 * pages/WaitingPage.jsx
 *
 * Shows the To-Be-Assigned list and a form to create new task chunks.
 * This page is the most interactive — it covers Section 8.1 of the spec.
 */

import { useEffect, useState } from 'react'
import { getWaitingList, createTaskChunk, acknowledgeBreachApi, listGoals } from '../services/api'
import TaskChunkCard from '../components/TaskChunkCard'
import AssignModal from '../components/AssignModal'
import { URGENCY_OPTIONS } from '../utils/urgency'

const INITIAL_FORM = {
  content: '',
  time_period: '',
  time_divergent: '',
  urgency_label: 'Low',
  goal_id: '',
  reference_link: '',
}

export default function WaitingPage() {
  const [chunks, setChunks] = useState([])
  const [goals, setGoals] = useState([])
  const [form, setForm] = useState(INITIAL_FORM)
  const [assigning, setAssigning] = useState(null)  // chunk being assigned
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  function load() {
    setLoading(true)
    Promise.all([getWaitingList(), listGoals()])
      .then(([c, g]) => { setChunks(c); setGoals(g) })
      .catch(() => setError('Failed to load data.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function handleField(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleCreate(e) {
    e.preventDefault()
    setFormError(null)
    if (!form.content.trim()) { setFormError('Content is required.'); return }
    if (!form.time_period || isNaN(Number(form.time_period))) {
      setFormError('Time period must be a number.')
      return
    }
    setSubmitting(true)
    try {
      await createTaskChunk({
        content: form.content.trim(),
        time_period: Number(form.time_period),
        time_divergent: form.time_divergent ? Number(form.time_divergent) : 0,
        urgency_label: form.urgency_label,
        goal_id: form.goal_id || undefined,
        reference_link: form.reference_link || undefined,
      })
      setForm(INITIAL_FORM)
      load()
    } catch (e) {
      setFormError(e.response?.data?.detail || 'Failed to create task chunk.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAck(chunkId) {
    try {
      await acknowledgeBreachApi(chunkId)
      load()
    } catch {
      setError('Failed to acknowledge breach.')
    }
  }

  function handleAssignSuccess() {
    setAssigning(null)
    load()
  }

  return (
    <div style={{ padding: 32, maxWidth: 960, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>
        To-Be-Assigned ({chunks.length})
      </h1>

      {/* Create form */}
      <div className="card" style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>New Task Chunk</h2>
        {formError && <div className="error-msg">{formError}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Time Period (hrs) *
            </span>
            <input name="time_period" type="number" min="1" value={form.time_period} onChange={handleField} />
          </label>
          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Uncertainty ± (hrs)
            </span>
            <input name="time_divergent" type="number" min="0" value={form.time_divergent} onChange={handleField} />
          </label>
        </div>

        <label style={{ display: 'block', marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Content *
          </span>
          <textarea
            name="content"
            rows={3}
            value={form.content}
            onChange={handleField}
            placeholder="Describe what needs to be done…"
          />
        </label>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Urgency
            </span>
            <select name="urgency_label" value={form.urgency_label} onChange={handleField}>
              {URGENCY_OPTIONS.map(o => <option key={o}>{o}</option>)}
            </select>
          </label>
          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Goal (optional)
            </span>
            <select name="goal_id" value={form.goal_id} onChange={handleField}>
              <option value="">— None —</option>
              {goals.map(g => <option key={g.goal_id} value={g.goal_id}>{g.goal_id} — {g.title}</option>)}
            </select>
          </label>
        </div>

        <label style={{ display: 'block', marginBottom: 16 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
            Reference Link (optional)
          </span>
          <input name="reference_link" type="url" value={form.reference_link} onChange={handleField} placeholder="https://…" />
        </label>

        <button className="btn-primary" onClick={handleCreate} disabled={submitting}>
          {submitting ? 'Creating…' : '+ Create Task Chunk'}
        </button>
      </div>

      {/* List */}
      {error && <div className="error-msg">{error}</div>}
      {loading && <p style={{ color: 'var(--text-muted)' }}>Loading…</p>}
      {!loading && chunks.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>No task chunks waiting. Create one above.</p>
      )}
      {chunks.map(c => (
        <TaskChunkCard
          key={c.chunk_id}
          chunk={c}
          onAssign={setAssigning}
          onAck={handleAck}
        />
      ))}

      {assigning && (
        <AssignModal
          chunk={assigning}
          onClose={() => setAssigning(null)}
          onSuccess={handleAssignSuccess}
        />
      )}
    </div>
  )
}
