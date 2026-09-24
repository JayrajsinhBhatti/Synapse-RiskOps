/**
 * frontend/src/utils/formatters.js
 * Owner: Person 2 | Week: 6
 * 
 * Shared UI formatting helpers for timestamps, MTTR, risk scores,
 * severity badges, and service health chips.
 */

/**
 * Format ISO timestamp into a localized readable date-time string.
 */
export function formatTimestamp(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Format ISO timestamp into relative time ("X min ago", "just now").
 */
export function formatTimeAgo(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    if (diffSeconds < 5) return 'just now';
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return dateStr;
  }
}

/**
 * Format MTTR duration into human-readable minutes and seconds.
 */
export function formatMTTR(minutes) {
  if (minutes === null || minutes === undefined) return 'N/A';
  const totalSeconds = Math.round(Number(minutes) * 60);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

/**
 * Get CSS badge styling and label for an incident severity.
 */
export function getSeverityBadge(severity) {
  const sev = (severity || '').toLowerCase();
  switch (sev) {
    case 'critical':
      return {
        bg: 'bg-red-500/20',
        text: 'text-red-400',
        border: 'border-red-500/30',
        dot: 'bg-red-400',
        label: 'CRITICAL',
      };
    case 'high':
      return {
        bg: 'bg-rose-500/20',
        text: 'text-rose-400',
        border: 'border-rose-500/30',
        dot: 'bg-rose-400',
        label: 'HIGH',
      };
    case 'medium':
      return {
        bg: 'bg-amber-500/20',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        dot: 'bg-amber-400',
        label: 'MEDIUM',
      };
    case 'low':
    default:
      return {
        bg: 'bg-blue-500/20',
        text: 'text-blue-400',
        border: 'border-blue-500/30',
        dot: 'bg-blue-400',
        label: 'LOW',
      };
  }
}

/**
 * Get CSS badge styling for an incident status.
 */
export function getStatusBadge(status) {
  const st = (status || '').toLowerCase();
  switch (st) {
    case 'open':
      return {
        bg: 'bg-red-500/20',
        text: 'text-red-300',
        border: 'border-red-500/40',
        dot: 'bg-red-400 animate-pulse',
        label: 'Open',
      };
    case 'investigating':
      return {
        bg: 'bg-amber-500/20',
        text: 'text-amber-300',
        border: 'border-amber-500/40',
        dot: 'bg-amber-400 animate-ping',
        label: 'Investigating',
      };
    case 'mitigated':
      return {
        bg: 'bg-indigo-500/20',
        text: 'text-indigo-300',
        border: 'border-indigo-500/40',
        dot: 'bg-indigo-400',
        label: 'Mitigated',
      };
    case 'resolved':
      return {
        bg: 'bg-emerald-500/20',
        text: 'text-emerald-300',
        border: 'border-emerald-500/40',
        dot: 'bg-emerald-400',
        label: 'Resolved',
      };
    default:
      return {
        bg: 'bg-slate-700/40',
        text: 'text-slate-300',
        border: 'border-slate-600',
        dot: 'bg-slate-400',
        label: status || 'Unknown',
      };
  }
}

/**
 * Return tiered color values and categories for risk scores.
 * Tier thresholds:
 * - < 0.40: Low / Healthy
 * - 0.40 - 0.69: Medium / Watch
 * - >= 0.70: High / Critical
 */
export function getRiskScoreStyle(score) {
  const num = Number(score) || 0;
  if (num >= 0.70) {
    return {
      tier: 'Critical',
      color: '#ef4444',
      bgClass: 'bg-red-500/20',
      textClass: 'text-red-400',
      borderClass: 'border-red-500/40',
      progressClass: 'bg-red-500',
    };
  }
  if (num >= 0.40) {
    return {
      tier: 'Watch',
      color: '#f59e0b',
      bgClass: 'bg-amber-500/20',
      textClass: 'text-amber-400',
      borderClass: 'border-amber-500/40',
      progressClass: 'bg-amber-500',
    };
  }
  return {
    tier: 'Healthy',
    color: '#10b981',
    bgClass: 'bg-emerald-500/20',
    textClass: 'text-emerald-400',
    borderClass: 'border-emerald-500/40',
    progressClass: 'bg-emerald-500',
  };
}

/**
 * Return health status badge styling for microservices.
 */
export function getServiceHealthBadge(healthStatus) {
  const hs = (healthStatus || '').toLowerCase();
  switch (hs) {
    case 'healthy':
      return {
        bg: 'bg-emerald-500/10',
        text: 'text-emerald-400',
        border: 'border-emerald-500/30',
        dot: 'bg-emerald-400',
      };
    case 'degraded':
      return {
        bg: 'bg-amber-500/10',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        dot: 'bg-amber-400 animate-pulse',
      };
    case 'critical':
      return {
        bg: 'bg-red-500/10',
        text: 'text-red-400',
        border: 'border-red-500/30',
        dot: 'bg-red-400 animate-ping',
      };
    default:
      return {
        bg: 'bg-slate-700/20',
        text: 'text-slate-400',
        border: 'border-slate-700',
        dot: 'bg-slate-400',
      };
  }
}
