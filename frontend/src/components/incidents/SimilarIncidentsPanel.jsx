/**
 * frontend/src/components/incidents/SimilarIncidentsPanel.jsx
 * 
 * Similar Past Incident Matching & Organizational Memory.
 * Implements Top 5 Feature #5 & Section 10 P1 #6.
 * 
 * Finds historical incidents on the same microservice with matching failure types,
 * surfacing previous root causes, successful playbooks, and historical MTTR.
 */

import React from 'react';
import { useSimilarIncidents } from '../../hooks/useAnalytics';
import {
  History,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  BookOpen,
  Play,
  RotateCcw,
} from 'lucide-react';
import { formatTimeAgo } from '../../utils/formatters';

export default function SimilarIncidentsPanel({ incidentId, onApplyPlaybook }) {
  const { data: similarIncidents, isLoading } = useSimilarIncidents(incidentId);

  if (isLoading) {
    return (
      <div className="p-4 text-center">
        <Clock className="w-5 h-5 text-cyan-400 animate-spin mx-auto mb-2" />
        <span className="text-xs font-mono text-slate-400">Searching incident memory bank...</span>
      </div>
    );
  }

  const items = Array.isArray(similarIncidents) ? similarIncidents : [];

  if (items.length === 0) {
    return (
      <div className="p-4 text-center rounded-xl dark:bg-slate-900/60 bg-slate-50 border dark:border-slate-800 border-slate-200">
        <History className="w-6 h-6 text-slate-500 mx-auto mb-1.5" />
        <div className="text-xs font-semibold dark:text-slate-300 text-slate-700">No Past Matches Found</div>
        <div className="text-[11px] text-slate-400">
          This is an unprecedented failure pattern for this service.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider dark:text-slate-400 text-slate-500 flex items-center gap-1.5">
          <History className="w-3.5 h-3.5 text-cyan-400" />
          Organizational Memory — Similar Past Incidents ({items.length})
        </span>
        <span className="text-[10px] font-mono text-cyan-400">Ranked by similarity</span>
      </div>

      <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
        {items.map((item) => (
          <div
            key={item.id}
            className="p-3 rounded-xl dark:bg-slate-900/80 bg-slate-50 border dark:border-slate-800 border-slate-200 hover:border-cyan-500/30 transition-all space-y-2"
          >
            {/* Header: Title, Similarity Score, Resolved Duration */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-xs font-bold dark:text-white text-slate-900 line-clamp-1">
                  {item.title}
                </div>
                <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5 font-mono">
                  <span>Resolved in {item.duration_formatted}</span>
                  <span>•</span>
                  <span>{formatTimeAgo(item.resolved_at)}</span>
                </div>
              </div>

              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 font-bold border border-cyan-500/20 shrink-0">
                {Math.round(item.similarity_score * 100)}% Match
              </span>
            </div>

            {/* Root Cause & Resolution */}
            <div className="text-[11px] space-y-1 dark:bg-slate-950/60 bg-white p-2 rounded-lg border dark:border-slate-800/80 border-slate-200">
              <div className="dark:text-slate-300 text-slate-700">
                <strong className="text-slate-400">Previous Cause: </strong>
                {item.root_cause}
              </div>
              <div className="text-emerald-500 dark:text-emerald-400 flex items-center justify-between gap-2 mt-1">
                <span>
                  <strong>Fix: </strong>
                  {item.guidance || 'Restarted pool & scaled replicas'}
                </span>
              </div>
            </div>

            {/* Playbook executed */}
            {item.resolution_action && (
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1">
                <span className="truncate max-w-[220px]">
                  Playbook: {item.resolution_action}
                </span>
                {onApplyPlaybook && (
                  <button
                    onClick={() => onApplyPlaybook(item)}
                    className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                  >
                    <span>Use Previous Fix</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
