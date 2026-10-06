/**
 * frontend/src/components/common/Badge.jsx
 * 
 * Reusable Status & Severity Badge primitive.
 */

import React from 'react';

export function Badge({ variant = 'default', children, className = '', dot = false }) {
  const variantStyles = {
    default: 'bg-slate-800/80 text-slate-300 border-slate-700/60',
    primary: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    danger: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    critical: 'bg-red-500/15 text-red-400 border-red-500/40 shadow-glow-danger',
  };

  const dotStyles = {
    default: 'bg-slate-400',
    primary: 'bg-indigo-400',
    cyan: 'bg-cyan-400',
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    danger: 'bg-rose-400',
    critical: 'bg-red-500 animate-pulse',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors ${
        variantStyles[variant] || variantStyles.default
      } ${className}`}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            dotStyles[variant] || dotStyles.default
          }`}
        />
      )}
      {children}
    </span>
  );
}

export default Badge;
