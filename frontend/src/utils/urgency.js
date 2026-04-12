/**
 * utils/urgency.js
 * Shared helpers for rendering urgency labels and status badges.
 * Used by multiple components — defined once here.
 */

export const URGENCY_COLORS = {
  'Very High': 'var(--urgency-1)',
  'High':      'var(--urgency-2)',
  'Medium':    'var(--urgency-3)',
  'Low':       'var(--urgency-4)',
  'Very Low':  'var(--urgency-5)',
}

export const STATUS_COLORS = {
  'OK':             'var(--status-ok)',
  'BREACH':         'var(--status-breach)',
  'BREACH_ACTION':  'var(--status-breach-action)',
  'IN_PROGRESS':    'var(--status-in-progress)',
  'COMPLETED':      'var(--status-completed)',
  'FAILED':         'var(--status-failed)',
}

export const STATUS_LABELS = {
  'OK':             'OK',
  'BREACH':         'Breach',
  'BREACH_ACTION':  'Breach — Action Required',
  'IN_PROGRESS':    'In Progress',
  'COMPLETED':      'Completed',
  'FAILED':         'Failed',
}

export const URGENCY_OPTIONS = ['Very High', 'High', 'Medium', 'Low', 'Very Low']

export function formatTimeRange(period, divergent) {
  if (!divergent) return `${period}h`
  return `${period - divergent}–${period + divergent}h`
}
