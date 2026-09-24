/**
 * frontend/src/components/IncidentTimeline.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Chronological incident feed and audit trail.
 * Displays state transitions (prediction -> diagnosis -> routing -> automation -> recovery),
 * MTTR calculations, severity badges, and quick status mutation triggers.
 */

import React, { useState, useMemo } from 'react';
import { useIncidents, useServices, useUpdateIncidentStatus } from '../hooks/useIncidents';
import { useAuth } from '../context/AuthContext';
import {
  formatTimestamp,
  formatTimeAgo,
  formatMTTR,
  getSeverityBadge,
  getStatusBadge,
} from '../utils/formatters';
import {
  AlertCircle,
  Clock,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  ArrowRight,
  ShieldAlert,
  PlayCircle,
  RefreshCw,
} from 'lucide-react';

export default function IncidentTimeline({
  selectedIncidentId,
  onSelectIncident,
  onOpenGuidance,
}) {
  const { data: incidentsData, isLoading, refetch } = useIncidents();
  const { data: servicesData } = useServices();
  const updateStatusMutation = useUpdateIncidentStatus();
  const { canRemediate, openAuthModal } = useAuth();

  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const incidents = useMemo(() => {
    return Array.isArray(incidentsData) ? incidentsData : [];
  }, [incidentsData]);

  // Lookup map: Service UUID -> Friendly Name
  const serviceMap = useMemo(() => {
    const map = {};
    if (Array.isArray(servicesData)) {
      servicesData.forEach((s) => {
        map[s.id] = s.service_name || s.name;
      });
    }
    return map;
  }, [servicesData]);

  // Filtered incidents
  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      if (statusFilter !== 'ALL' && inc.status.toUpperCase() !== statusFilter) {
        return false;
      }
      if (severityFilter !== 'ALL' && inc.severity.toUpperCase() !== severityFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const serviceName = (serviceMap[inc.service_id] || inc.service_id || '').toLowerCase();
        const matchesTitle = inc.title?.toLowerCase().includes(query);
        const matchesService = serviceName.includes(query);
        const matchesDesc = inc.description?.toLowerCase().includes(query);
        if (!matchesTitle && !matchesService && !matchesDesc) return false;
      }
      return true;
    });
  }, [incidents, statusFilter, severityFilter, searchQuery, serviceMap]);

  const handleAcknowledge = async (e, inc) => {
    e.stopPropagation();
    if (!canRemediate) {
      openAuthModal();
      return;
    }
    await updateStatusMutation.mutateAsync({
      incidentId: inc.id,
      status: 'INVESTIGATING',
      comment: 'Acknowledged by on-call engineer for investigation.',
    });
  };

  const handleResolve = async (e, inc) => {
    e.stopPropagation();
    if (!canRemediate) {
      openAuthModal();
      return;
    }
    await updateStatusMutation.mutateAsync({
      incidentId: inc.id,
      status: 'RESOLVED',
      comment: 'Verification completed. System health metrics normalized.',
    });
  };

  const toggleExpand = (e, id) => {
    e.stopPropagation();
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="glass-card flex flex-col h-full overflow-hidden">
      {/* Header & Controls */}
      <div className="p-4 border-b border-white/10 space-y-3 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
            <h2 className="text-base font-bold text-white tracking-wide">
              Incident Feed & Audit History
            </h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {filteredIncidents.length}
            </span>
          </div>

          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Refresh Feed"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Filters */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search incidents or services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-synapse-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-synapse-500"
          >
            <option value="ALL">All Status</option>
            <option value="OPEN">Open</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="MITIGATED">Mitigated</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-synapse-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Incident List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            Loading incident records...
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs flex flex-col items-center gap-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500/50" />
            <span>No incidents matching the selected criteria</span>
          </div>
        ) : (
          filteredIncidents.map((inc) => {
            const isSelected = selectedIncidentId === inc.id;
            const isExpanded = expandedId === inc.id;
            const sevBadge = getSeverityBadge(inc.severity);
            const statusBadge = getStatusBadge(inc.status);
            const serviceFriendlyName = serviceMap[inc.service_id] || inc.service_id || 'Global';

            return (
              <div
                key={inc.id}
                onClick={() => {
                  if (onSelectIncident) onSelectIncident(inc);
                }}
                className={`rounded-xl border p-3.5 transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/90 border-synapse-500 shadow-lg shadow-synapse-500/15'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                }`}
              >
                {/* Top Row: Severity, Status, Service, Time */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sevBadge.bg} ${sevBadge.text} ${sevBadge.border} flex items-center gap-1`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${sevBadge.dot}`} />
                      {sevBadge.label}
                    </span>

                    <span
                      className={`text-[10px] font-medium px-2 py-0.5 rounded-md border ${statusBadge.bg} ${statusBadge.text} ${statusBadge.border} flex items-center gap-1`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
                      {statusBadge.label}
                    </span>

                    <span className="text-[10px] text-slate-300 font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                      {serviceFriendlyName}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-[11px] text-slate-400">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimeAgo(inc.created_at || inc.detected_at)}</span>
                  </div>
                </div>

                {/* Title & Description */}
                <h3 className="text-xs font-bold text-white mb-1 leading-snug">
                  {inc.title}
                </h3>
                <p className="text-[11px] text-slate-400 line-clamp-2 mb-3">
                  {inc.description}
                </p>

                {/* Bottom Row: Actions & Audit Toggle */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[11px]">
                  <div className="flex items-center gap-3">
                    {inc.status === 'OPEN' && (
                      <button
                        onClick={(e) => handleAcknowledge(e, inc)}
                        disabled={updateStatusMutation.isPending}
                        className="px-2.5 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-medium border border-amber-500/30 transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}

                    {(inc.status === 'OPEN' || inc.status === 'INVESTIGATING') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onSelectIncident) onSelectIncident(inc);
                          if (onOpenGuidance) onOpenGuidance();
                        }}
                        className="px-2.5 py-1 rounded-md bg-synapse-600 hover:bg-synapse-500 text-white font-medium shadow-sm transition-colors flex items-center gap-1"
                      >
                        <PlayCircle className="w-3.5 h-3.5" />
                        Remediate
                      </button>
                    )}

                    {inc.status === 'MITIGATED' && (
                      <button
                        onClick={(e) => handleResolve(e, inc)}
                        disabled={updateStatusMutation.isPending}
                        className="px-2.5 py-1 rounded-md bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 font-medium border border-emerald-500/30 transition-colors"
                      >
                        Verify & Resolve
                      </button>
                    )}

                    {inc.resolved_at && (
                      <span className="text-emerald-400 text-[10px] font-mono">
                        Resolved
                      </span>
                    )}
                  </div>

                  {/* Audit Trail Expand Toggle */}
                  <button
                    onClick={(e) => toggleExpand(e, inc.id)}
                    className="text-slate-400 hover:text-white flex items-center gap-0.5 text-[10px]"
                  >
                    <span>Audit Trail</span>
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>

                {/* Expanded Audit Trail Drawer */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-slate-800 space-y-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Chronological State Transitions
                    </span>
                    {(!inc.history || inc.history.length === 0) ? (
                      <div className="text-[10px] text-slate-500 italic">
                        Initial incident ingestion logged. No further transitions yet.
                      </div>
                    ) : (
                      inc.history.map((hist, idx) => (
                        <div
                          key={idx}
                          className="p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-[10px] space-y-1"
                        >
                          <div className="flex items-center justify-between text-slate-400">
                            <span className="font-semibold text-slate-300">
                              {hist.action || 'MUTATION'}: {hist.old_value || 'OPEN'} <ArrowRight className="w-2.5 h-2.5 inline mx-1" /> {hist.new_value || hist.action}
                            </span>
                            <span>{formatTimestamp(hist.changed_at || hist.timestamp)}</span>
                          </div>
                          <div className="text-slate-500 text-[9px]">
                            Actor: {hist.changed_by || 'Autonomous Orchestrator'}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
