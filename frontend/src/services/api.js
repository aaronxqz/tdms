/**
 * services/api.js
 *
 * One file owns all communication with the backend.
 * Components never call fetch() directly — they always go through here.
 * That way if the API URL changes, you change it in one place.
 */

import axios from 'axios'

// All requests go through Vite's proxy: /api → http://localhost:8000
const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── Goals ────────────────────────────────────────────────────────────────────

export const createGoal = (data) => api.post('/goals/', data).then(r => r.data)
export const listGoals = () => api.get('/goals/').then(r => r.data)
export const getGoal = (goalId) => api.get(`/goals/${goalId}`).then(r => r.data)

// ── Task Chunks ───────────────────────────────────────────────────────────────

export const createTaskChunk = (data) => api.post('/tasks/', data).then(r => r.data)
export const getWaitingList = () => api.get('/tasks/waiting').then(r => r.data)
export const getAssignedList = () => api.get('/tasks/assigned').then(r => r.data)
export const getTaskChunk = (chunkId) => api.get(`/tasks/${chunkId}`).then(r => r.data)
export const updateTaskChunk = (chunkId, data) => api.patch(`/tasks/${chunkId}`, data).then(r => r.data)

export const assignTaskChunk = (chunkId, data) =>
  api.post(`/tasks/${chunkId}/assign`, data).then(r => r.data)

export const acknowledgeBreachApi = (chunkId) =>
  api.post(`/tasks/${chunkId}/ack`).then(r => r.data)

export const completeTaskChunk = (chunkId, note) =>
  api.post(`/tasks/${chunkId}/complete`, null, { params: { note } }).then(r => r.data)

export const failTaskChunk = (chunkId, note) =>
  api.post(`/tasks/${chunkId}/fail`, null, { params: { note } }).then(r => r.data)

export const searchTaskChunks = (params) =>
  api.get('/tasks/search', { params }).then(r => r.data)

export const getDashboard = () => api.get('/tasks/dashboard').then(r => r.data)
