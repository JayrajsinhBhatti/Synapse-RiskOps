/**
 * frontend/src/components/observability/ChangeEventTimeline.jsx
 * 
 * Change Event Timeline ("What Changed?").
 * Implements Section 10 P1 #9 & UX Weakness #5.
 * 
 * Displays deployments, config pushes, and canary rollouts correlated with
 * active microservice incidents, allowing SREs to answer "what changed before this?"
 */

import React, { useState } from 'react';
import { useChangeEvents } from '../../hooks/useAnalytics';
import {
  GitCommit,
  GitBranch,
  Layers,
  RotateCcw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  User,
  ExternalLink,
} from 'lucide-react';
import { formatTimeAgo } from '../../utils/formatters';

export default function ChangeEventTimeline({ serviceName }) {
  const { data: changeEvents, isLoading } = useChangeEvents({ serviceName });
  const [rolledBackIds, setRolledBackIds] = useState(new Set());

  const handleRollback = (eventId) => {
    setRolledBackIds((prev) => new Set([...prev, eventId]));
  };

  if (isLoading) {
    return (
      <div className="p-4 text-center">
        <Clock className="w-5 h-5 text-cyan-400 animate-spin mx-auto mb-2" />
        <span className="text-xs font-mono text-slate-400">Loading change events...</span>
      </div>
    );
  }

  const events = Array.isArray(changeEvents) ? changeEvents : [];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider dark:text-slate-400 text-slate-500 flex items-center gap-1.5">
          <GitCommit className="w-3.5 h-3.5 text-purple-400" />
          Change Intelligence — Deployments & Config Timeline
        </span>
        <span className="text-[10px] font-mono text-purple-400">CI/CD & Kubernetes Events</span>
      </div>

      <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
        {events.map((evt) => {
          const isRolledBack = rolledBackIds.has(evt.id);
          return (
            <div
              key={evt.id}
              className={`p-3 rounded-xl border transition-all space-y-2 ${
                evt.correlated_with_incident
                  ? 'dark:bg-red-500/10 bg-red-50/60 dark:border-red-500/30 border-red-200'
                  : 'dark:bg-slate-900/80 bg-slate-50 dark:border-slate-800 border-slate-200'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold dark:text-white text-slate-900">
                      {evt.title}
                    </span>
                    {evt.correlated_with_incident && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 uppercase tracking-wider animate-pulse">
                        Correlated to Incident
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5 font-mono">
                    <span>{evt.service_name}</span>
                    <span>•</span>
                    <span>{formatTimeAgo(evt.timestamp)}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <User className="w-2.5 h-2.5" />
                      {evt.author}
                    </span>
                  </div>
                </div>

                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/15 text-purple-400 font-semibold border border-purple-500/20">
                  {evt.change_type}
                </span>
              </div>

              <p className="text-[11px] dark:text-slate-300 text-slate-600 dark:bg-slate-950/50 bg-white p-2 rounded-lg border dark:border-slate-800/80 border-slate-200">
                {evt.description}
              </p>

              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1">
                <span>Commit: <span className="text-cyan-400 font-semibold">{evt.commit_sha}</span></span>
                
                {evt.rollback_supported && (
                  <button
                    onClick={() => handleRollback(evt.id)}
                    disabled={isRolledBack}
                    className={`flex items-center gap-1 font-semibold px-2 py-1 rounded transition-colors ${
                      isRolledBack
                        ? 'bg-emerald-500/15 text-emerald-400 cursor-not-allowed'
                        : 'bg-red-500/15 text-red-400 hover:bg-red-500/25'
                    }`}
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>{isRolledBack ? 'Rollback Dispatched' : 'Rollback to Previous SHA'}</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
