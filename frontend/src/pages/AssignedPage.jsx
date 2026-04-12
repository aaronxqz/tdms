import { useEffect, useState } from 'react'
import { getAssignedList, completeTaskChunk, failTaskChunk } from '../services/api'
import TaskChunkCard from '../components/TaskChunkCard'

export default function AssignedPage() {
  const [chunks, setChunks] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    getAssignedList()
      .then(setChunks)
      .catch(() => setError('Failed to load assigned list.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function handleComplete(chunkId) {
    try { await completeTaskChunk(chunkId); load() }
    catch { setError('Failed to complete chunk.') }
  }

  async function handleFail(chunkId) {
    try { await failTaskChunk(chunkId); load() }
    catch { setError('Failed to mark chunk as failed.') }
  }

  return (
    <div style={{ padding: 32, maxWidth: 960, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>
        Assigned / In Progress ({chunks.length})
      </h1>
      {error && <div className="error-msg">{error}</div>}
      {loading && <p style={{ color: 'var(--text-muted)' }}>Loading…</p>}
      {!loading && chunks.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>No task chunks currently in progress.</p>
      )}
      {chunks.map(c => (
        <TaskChunkCard
          key={c.chunk_id}
          chunk={c}
          onComplete={handleComplete}
          onFail={handleFail}
        />
      ))}
    </div>
  )
}
