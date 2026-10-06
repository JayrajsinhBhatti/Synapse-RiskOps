/**
 * frontend/src/components/common/EmptyState.jsx
 * 
 * Production-ready Empty, Loading, and Error state visualizer.
 */

import React from 'react';
import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import Button from './Button';

export function EmptyState({
  type = 'empty', // 'empty' | 'loading' | 'error'
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) {
  if (type === 'loading') {
    return (
      <div className={`flex flex-col items-center justify-center p-12 text-center text-slate-400 ${className}`}>
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
        <h4 className="text-sm font-semibold text-white">{title || 'Loading operational data...'}</h4>
        {description && <p className="text-xs text-slate-400 mt-1 max-w-sm">{description}</p>}
      </div>
    );
  }

  if (type === 'error') {
    return (
      <div className={`flex flex-col items-center justify-center p-12 text-center text-slate-400 ${className}`}>
        <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-3 shadow-glow-danger">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-white">{title || 'Failed to load telemetry'}</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-sm">
          {description || 'An error occurred while communicating with the Synapse RiskOps pipeline.'}
        </p>
        {onAction && (
          <Button variant="secondary" size="sm" onClick={onAction} icon={RefreshCw} className="mt-4">
            {actionLabel || 'Retry Request'}
          </Button>
        )}
      </div>
    );
  }

  // Default: Empty
  const FallbackIcon = Icon || CheckCircle2;
  return (
    <div className={`flex flex-col items-center justify-center p-12 text-center text-slate-400 ${className}`}>
      <div className="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-400 mb-3">
        <FallbackIcon className="w-6 h-6 text-slate-300" />
      </div>
      <h4 className="text-sm font-semibold text-white">{title || 'No records found'}</h4>
      <p className="text-xs text-slate-400 mt-1 max-w-sm">
        {description || "You're all clear. No active items match the current criteria."}
      </p>
      {onAction && actionLabel && (
        <Button variant="secondary" size="sm" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

export default EmptyState;
