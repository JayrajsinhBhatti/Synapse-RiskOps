/**
 * frontend/src/components/incidents/IncidentsManagementView.jsx
 * 
 * Production Incident Management & Audit Console.
 * Implements Prompt Section 21 & Phase 7:
 * - Filter by status (ALL, OPEN, INVESTIGATING, RESOLVED) and severity (ALL, CRITICAL, HIGH, etc.)
 * - Direct status transition buttons (Acknowledge, Investigate, Resolve)
 * - Chronological audit history drawer backed by GET /api/incidents/{id}/history
 * - Real-time SSE synchronization.
 */

import React, { useState, useMemo } from 'react';
import {
  useIncidents,
  useServices,
  useIncidentHistory,
  useUpdateIncidentStatus,
  useDeleteIncident,
  useDeleteIncidentHistory,
  useDeleteAllIncidents,
  useRetentionSettings,
  useUpdateRetentionSettings,
} from '../../hooks/useIncidents';
import { useAuth } from '../../context/AuthContext';
import { useWorkspace } from '../../context/WorkspaceContext';
import { getSeverityBadge, getStatusBadge } from '../../utils/formatters';
import GuidancePanel from '../GuidancePanel';
import {
  AlertOctagon,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Activity,
  History,
  ShieldAlert,
  ArrowRight,
  Server,
  Zap,
  User,
  ChevronRight,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Calendar,
  X,
} from 'lucide-react';

export default function IncidentsManagementView({ onSelectService }) {
  const { user, role } = useAuth();
  const { mode } = useWorkspace();
  const { data: incidentsData, isLoading } = useIncidents();
  const { data: servicesData } = useServices();
  const updateStatusMutation = useUpdateIncidentStatus();
  const deleteIncidentMutation = useDeleteIncident();
  const deleteHistoryMutation = useDeleteIncidentHistory();
  const deleteAllIncidentsMutation = useDeleteAllIncidents();
  const { data: retentionData } = useRetentionSettings();
  const updateRetentionMutation = useUpdateRetentionSettings();

  const incidents = Array.isArray(incidentsData) ? incidentsData : [];
  const services = Array.isArray(servicesData) ? servicesData : [];

  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('guidance'); // 'guidance' | 'audit'

  // Modals for safe deletion
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleteAllModalOpen, setIsDeleteAllModalOpen] = useState(false);
  const [deleteAllConfirmText, setDeleteAllConfirmText] = useState('');
  const [deleteError, setDeleteError] = useState(null);

  const serviceMap = useMemo(() => {
    const map = {};
    services.forEach((s) => {
      map[s.id] = s.service_name || s.name;
    });
    return map;
  }, [services]);

  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      const svcName = serviceMap[inc.service_id] || '';
      const matchesSearch =
        inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        svcName.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || inc.status === statusFilter;
      const matchesSeverity = severityFilter === 'ALL' || inc.severity === severityFilter;
      return matchesSearch && matchesStatus && matchesSeverity;
    });
  }, [incidents, searchTerm, statusFilter, severityFilter, serviceMap]);

  // Active selected incident
  const activeIncident = useMemo(() => {
    if (selectedIncidentId) {
      return incidents.find((i) => i.id === selectedIncidentId) || filteredIncidents[0];
    }
    return filteredIncidents[0] || null;
  }, [incidents, selectedIncidentId, filteredIncidents]);

  const { data: historyData, isLoading: historyLoading } = useIncidentHistory(activeIncident?.id);
  const historyList = Array.isArray(historyData) ? historyData : [];

  const handleStatusChange = async (incidentId, newStatus) => {
    try {
      await updateStatusMutation.mutateAsync({
        incidentId,
        status: newStatus,
      });
    } catch (err) {
      console.error('Failed to update incident status:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="h-[calc(100vh-140px)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <AlertOctagon className="w-8 h-8 text-rose-400 animate-pulse" />
          <span className="text-xs font-mono text-slate-400">Loading Incident Feed & Audit Logs...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Top Header & Search/Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl dark:bg-slate-900/80 bg-white border dark:border-white/[0.08] border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
              Operations Control
            </span>
            <span className="text-xs font-mono dark:text-slate-400 text-slate-500">
              {filteredIncidents.length} Filtered / {incidents.length} Total Incidents
            </span>
          </div>
          <h1 className="text-xl font-black dark:text-white text-slate-900 tracking-tight">
            Incident Management & Audit Trails
          </h1>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search incidents or service..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl pl-8 pr-3 py-1.5 text-xs dark:text-slate-200 text-slate-800 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-rose-500 w-44 md:w-56"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl px-3 py-1.5 text-xs dark:text-slate-200 text-slate-800 font-medium focus:outline-none focus:border-rose-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl px-3 py-1.5 text-xs dark:text-slate-200 text-slate-800 font-medium focus:outline-none focus:border-rose-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Time-based Log Retention Dropdown */}
          <div className="flex items-center gap-1.5 dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl px-2.5 py-1.5 text-xs">
            <Calendar className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
            <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500 hidden sm:inline">Retention:</span>
            <select
              value={retentionData?.incidents_policy || 'all'}
              onChange={(e) => updateRetentionMutation.mutate({ incidents_policy: e.target.value })}
              disabled={updateRetentionMutation.isPending}
              className="bg-transparent text-xs font-semibold dark:text-slate-200 text-slate-800 focus:outline-none cursor-pointer"
              title="Time-based Log Retention: records older than this duration are automatically pruned"
            >
              <option value="1d">1 Day</option>
              <option value="7d">7 Days</option>
              <option value="30d">30 Days</option>
              <option value="90d">90 Days</option>
              <option value="all">All Time</option>
            </select>
          </div>

          {/* Purge All Incidents for active mode */}
          <button
            type="button"
            onClick={() => {
              setDeleteError(null);
              setDeleteAllConfirmText('');
              setIsDeleteAllModalOpen(true);
            }}
            className="px-2.5 py-1.5 rounded-xl border dark:border-rose-500/30 border-rose-200 bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            title="Purge all incidents for the active data mode"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Purge All</span>
          </button>
        </div>
      </div>

      {/* Main Split Console: Feed on Left, Details/Guidance on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[640px]">
        {/* Left: Incident Feed */}
        <div className="lg:col-span-5 space-y-3">
          {filteredIncidents.length === 0 ? (
            <div className="glass-card p-8 text-center text-slate-500">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <div className="text-sm font-bold dark:text-white text-slate-900 mb-1">You're all clear.</div>
              <div className="text-xs dark:text-slate-400 text-slate-500">No incidents match your current filter parameters.</div>
            </div>
          ) : (
            filteredIncidents.map((inc) => {
              const isSelected = activeIncident?.id === inc.id;
              const sev = getSeverityBadge(inc.severity);
              const stat = getStatusBadge(inc.status);
              const svcName = serviceMap[inc.service_id] || 'system-service';

              return (
                <div
                  key={inc.id}
                  onClick={() => setSelectedIncidentId(inc.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'dark:bg-slate-900 bg-indigo-50/80 border-indigo-500 shadow-md shadow-indigo-500/10'
                      : 'dark:bg-slate-900/60 bg-white border dark:border-slate-800 border-slate-200 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900/90 shadow-sm'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sev.bg} ${sev.text} ${sev.border}`}>
                        {sev.label}
                      </span>
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md border ${stat.bg} ${stat.text} ${stat.border}`}>
                        {stat.label}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      {new Date(inc.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <h3 className="text-xs font-bold dark:text-white text-slate-900 mb-1.5 leading-snug">
                    {inc.title}
                  </h3>

                  <div className="flex items-center justify-between text-[11px] font-mono dark:text-slate-400 text-slate-500 pt-2 border-t dark:border-white/[0.04] border-slate-100">
                    <span className="flex items-center gap-1.5 text-indigo-600 dark:text-indigo-300">
                      <Server className="w-3 h-3" />
                      {svcName}
                    </span>
                    {inc.risk_score && (
                      <span className="text-rose-500 dark:text-rose-400 font-bold">
                        Risk: {Number(inc.risk_score).toFixed(0)}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: Selected Incident Detail, Action Triggers & Audit Log */}
        <div className="lg:col-span-7">
          {activeIncident ? (
            <div className="glass-card flex flex-col h-full overflow-hidden">
              {/* Context Header */}
              <div className="p-4 border-b dark:border-white/[0.08] border-slate-200 dark:bg-slate-900/60 bg-slate-50/90 flex flex-col gap-3">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono dark:text-slate-400 text-slate-500">
                        Incident #{activeIncident.id.slice(0, 8)}
                      </span>
                      <span className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 dark:bg-indigo-500/10 bg-indigo-50 px-2 py-0.5 rounded-md border dark:border-indigo-500/20 border-indigo-200">
                        {serviceMap[activeIncident.service_id] || 'payment-service'}
                      </span>
                    </div>
                    <h2 className="text-base font-bold dark:text-white text-slate-900">
                      {activeIncident.title}
                    </h2>
                  </div>

                  {/* Quick Action Transition Buttons */}
                  <div className="flex items-center gap-2">
                    {activeIncident.status === 'OPEN' && (
                      <button
                        onClick={() => handleStatusChange(activeIncident.id, 'INVESTIGATING')}
                        disabled={updateStatusMutation.isPending}
                        className="px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-600 dark:text-amber-300 font-bold text-xs flex items-center gap-1.5 transition-all"
                      >
                        <Activity className="w-3.5 h-3.5" />
                        Acknowledge & Investigate
                      </button>
                    )}
                    {activeIncident.status !== 'RESOLVED' && (
                      <button
                        onClick={() => handleStatusChange(activeIncident.id, 'RESOLVED')}
                        disabled={updateStatusMutation.isPending}
                        className="px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-600 dark:text-emerald-300 font-bold text-xs flex items-center gap-1.5 transition-all"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Mark Resolved
                      </button>
                    )}

                    {/* Delete Individual Incident Button */}
                    <button
                      type="button"
                      onClick={() => {
                        setDeleteError(null);
                        setIsDeleteModalOpen(true);
                      }}
                      className="p-1.5 rounded-lg border dark:border-rose-500/30 border-rose-200 text-rose-500 hover:bg-rose-500/15 transition-all"
                      title="Delete this incident and its audit history"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Subnav Tabs: AI Guidance vs Audit Trail */}
                <div className="flex items-center gap-2 border-t dark:border-white/[0.04] border-slate-200 pt-2">
                  <button
                    onClick={() => setActiveTab('guidance')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                      activeTab === 'guidance'
                        ? 'bg-synapse-600 text-white'
                        : 'dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-950 dark:hover:bg-slate-800 hover:bg-slate-200/60'
                    }`}
                  >
                    AI Guidance & Remediation
                  </button>
                  <button
                    onClick={() => setActiveTab('audit')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                      activeTab === 'audit'
                        ? 'bg-synapse-600 text-white'
                        : 'dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-950 dark:hover:bg-slate-800 hover:bg-slate-200/60'
                    }`}
                  >
                    <History className="w-3 h-3" />
                    Audit Trail ({historyList.length})
                  </button>
                </div>
              </div>

              {/* Tab Contents */}
              <div className="flex-1 overflow-y-auto p-4">
                {activeTab === 'guidance' ? (
                  <GuidancePanel incident={activeIncident} />
                ) : (
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold dark:text-slate-300 text-slate-700 uppercase tracking-wider mb-2">
                      Immutable Audit Trail History
                    </h3>

                    {historyLoading ? (
                      <div className="py-8 text-center text-xs font-mono dark:text-slate-400 text-slate-500">
                        Loading audit logs...
                      </div>
                    ) : historyList.length === 0 ? (
                      <div className="py-8 text-center text-xs text-slate-500 font-mono">
                        No audit history entries recorded yet.
                      </div>
                    ) : (
                      <div className="relative pl-6 border-l-2 dark:border-slate-800 border-slate-300 space-y-4">
                        {historyList.map((entry, idx) => (
                          <div key={entry.id || idx} className="relative">
                            <div className="absolute -left-[31px] top-1 w-3 h-3 rounded-full bg-indigo-500 border-2 dark:border-slate-950 border-white" />
                            <div className="p-3 rounded-xl dark:bg-slate-900/60 bg-slate-50 border dark:border-slate-800 border-slate-200 text-xs shadow-sm">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-bold text-indigo-600 dark:text-indigo-300 font-mono">
                                  {entry.action}
                                </span>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[10px] font-mono text-slate-400">
                                    {new Date(entry.changed_at).toLocaleString()}
                                  </span>
                                  {entry.id && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        deleteHistoryMutation.mutate({
                                          historyId: entry.id,
                                          incidentId: activeIncident.id,
                                        });
                                      }}
                                      disabled={deleteHistoryMutation.isPending}
                                      className="p-1 rounded text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
                                      title="Delete this audit log entry"
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </button>
                                  )}
                                </div>
                              </div>
                              <p className="dark:text-slate-300 text-slate-700 text-[11px] mb-2">
                                {entry.new_value || 'Status transition applied'}
                              </p>
                              {entry.old_value && (
                                <div className="text-[10px] font-mono dark:text-slate-500 text-slate-400">
                                  Previous State: <span className="dark:text-slate-400 text-slate-600">{entry.old_value}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-card h-full flex items-center justify-center text-slate-500 p-8 text-center text-xs">
              Select an incident from the left feed to inspect details and audit history.
            </div>
          )}
        </div>
      </div>

      {/* ========================================================
          CONFIRMATION MODAL: DELETE INDIVIDUAL INCIDENT
         ======================================================== */}
      {isDeleteModalOpen && activeIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md dark:bg-slate-900 bg-white rounded-2xl border dark:border-rose-500/30 border-rose-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-bold text-sm">
                <Trash2 className="w-5 h-5" />
                <span>Delete Incident #{activeIncident.id.slice(0, 8)}</span>
              </div>
              <button
                onClick={() => setIsDeleteModalOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs dark:text-slate-300 text-slate-700 leading-relaxed">
              Are you sure you want to permanently delete{' '}
              <strong className="dark:text-white text-slate-900">"{activeIncident.title}"</strong>?
              This will remove the incident record and all associated audit trail entries from the database immediately.
            </p>

            {deleteError && (
              <div className="p-3 rounded-lg dark:bg-rose-950/40 bg-rose-50 border border-rose-500/30 text-rose-500 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{deleteError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t dark:border-white/5 border-slate-100">
              <button
                type="button"
                onClick={() => setIsDeleteModalOpen(false)}
                className="px-3 py-1.5 rounded-lg dark:bg-slate-800 bg-slate-100 text-xs font-semibold dark:text-slate-300 text-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await deleteIncidentMutation.mutateAsync(activeIncident.id);
                    setIsDeleteModalOpen(false);
                    setSelectedIncidentId(null);
                  } catch (err) {
                    setDeleteError(err.message || 'Failed to delete incident.');
                  }
                }}
                disabled={deleteIncidentMutation.isPending}
                className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                {deleteIncidentMutation.isPending ? 'Deleting...' : 'Delete Incident'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          CONFIRMATION MODAL: PURGE ALL INCIDENTS (BULK)
         ======================================================== */}
      {isDeleteAllModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md dark:bg-slate-900 bg-white rounded-2xl border dark:border-rose-500/40 border-rose-300 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-bold text-sm">
                <AlertTriangle className="w-5 h-5 text-rose-500" />
                <span>Purge All Incidents ({mode.toUpperCase()} Mode)</span>
              </div>
              <button
                onClick={() => setIsDeleteAllModalOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-xl dark:bg-rose-950/30 bg-rose-50 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs space-y-1">
              <span className="font-bold block">Danger Zone: Irreversible Action</span>
              <p className="text-[11px] leading-relaxed">
                This will delete ALL incidents and their entire audit history records currently registered under the{' '}
                <strong>{mode}</strong> data mode. Real and demo records in the other mode remain untouched.
              </p>
            </div>

            {role !== 'ADMIN' && role !== 'SRE' ? (
              <div className="p-3 rounded-lg dark:bg-amber-950/30 bg-amber-50 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs">
                Your role (<strong>{role || 'VIEWER'}</strong>) is not authorized to purge all incidents.
                Only <strong>ADMIN</strong> or <strong>SRE</strong> roles can execute bulk module purges.
              </div>
            ) : (
              <div>
                <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                  Type <span className="font-mono text-rose-500 font-bold">DELETE ALL</span> to confirm:
                </label>
                <input
                  type="text"
                  value={deleteAllConfirmText}
                  onChange={(e) => setDeleteAllConfirmText(e.target.value)}
                  placeholder="DELETE ALL"
                  className="w-full px-3 py-2 dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 font-mono focus:outline-none focus:border-rose-500"
                />
              </div>
            )}

            {deleteError && (
              <div className="p-3 rounded-lg dark:bg-rose-950/40 bg-rose-50 border border-rose-500/30 text-rose-500 text-xs">
                {deleteError}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t dark:border-white/5 border-slate-100">
              <button
                type="button"
                onClick={() => setIsDeleteAllModalOpen(false)}
                className="px-3 py-1.5 rounded-lg dark:bg-slate-800 bg-slate-100 text-xs font-semibold dark:text-slate-300 text-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await deleteAllIncidentsMutation.mutateAsync(mode);
                    setIsDeleteAllModalOpen(false);
                    setSelectedIncidentId(null);
                  } catch (err) {
                    setDeleteError(err.message || 'Failed to purge incidents.');
                  }
                }}
                disabled={
                  deleteAllConfirmText !== 'DELETE ALL' ||
                  deleteAllIncidentsMutation.isPending ||
                  (role !== 'ADMIN' && role !== 'SRE')
                }
                className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleteAllIncidentsMutation.isPending ? 'Purging...' : 'Confirm Purge All'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
