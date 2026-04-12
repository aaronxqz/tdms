/**
 * pages/SearchPage.jsx
 *
 * Full-text and filtered search across all task chunks, including
 * completed and failed ones. Covers Section 7 of the spec.
 */

import { useState } from 'react'
import { searchTaskChunks } from '../services/api'
import TaskChunkCard from '../components/TaskChunkCard'
import { URGENCY_OPTIONS } from '../utils/urgency'

const STATUS_OPTIONS = ['OK', 'BREACH', 'BREACH_ACTION', 'IN_PROGRESS', 'COMPLETED', 'FAILED']

export default function SearchPage() {
  const [keyword, setKeyword]       = useState('')
  const [status, setStatus]         = useState('')
  const [urgency, setUrgency]       = useState('')
  const [goalId, setGoalId]         = useState('')
  const [results, setResults]       = useState(null)   // null = not searched yet
  const [error, setError]           = useState(null)
  const [loading, setLoading]       = useState(false)

  async function handleSearch() {
    setLoading(true)
    setError(null)
    try {
      const data = await searchTaskChunks({
        keyword:       keyword || undefined,
        status:        status  || undefined,
        urgency_label: urgency || undefined,
        goal_id:       goalId  || undefined,
      })
      setResults(data)
    } catch {
      setError('Search failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div style={{ padding: 32, maxWidth: 960, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Search</h1>

      {/* Filter bar */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Keyword
            </span>
            <input
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Search content or REF-XXXX…"
            />
          </label>

          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Status
            </span>
            <select value={status} onChange={e => setStatus(e.target.value)}>
              <option value="">All</option>
              {STATUS_OPTIONS.map(s => <option key={s}>{s}</option>)}
            </select>
          </label>

          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Urgency
            </span>
            <select value={urgency} onChange={e => setUrgency(e.target.value)}>
              <option value="">All</option>
              {URGENCY_OPTIONS.map(u => <option key={u}>{u}</option>)}
            </select>
          </label>

          <label>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Goal ID
            </span>
            <input
              value={goalId}
              onChange={e => setGoalId(e.target.value)}
              placeholder="e.g. GOAL-001"
            />
          </label>
        </div>

        <button className="btn-primary" onClick={handleSearch} disabled={loading}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {/* Results */}
      {error && <div className="error-msg">{error}</div>}

      {results === null && !loading && (
        <p style={{ color: 'var(--text-muted)' }}>Enter search criteria above and press Search.</p>
      )}

      {results !== null && (
        <p style={{ color: 'var(--text-muted)', marginBottom: 16, fontSize: 13 }}>
          {results.length} result{results.length !== 1 ? 's' : ''} found
        </p>
      )}

      {results?.map(c => (
        <TaskChunkCard key={c.chunk_id} chunk={c} />
      ))}
    </div>
  )
}
