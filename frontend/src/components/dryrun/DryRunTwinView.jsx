/**
 * frontend/src/components/dryrun/DryRunTwinView.jsx
 * 
 * Dry-Run Twin (Counterfactual Remediation) Console for Synapse RiskOps.
 * Simulates alternative remediation actions through predictive counterfactual
 * modeling before any real execution occurs.
 * 
 * Features:
 * - Multi-action counterfactual simulation (Scale, Restart, Rate Limit, Rollback, Circuit Breaker, Flush Cache)
 * - Side-by-side predictive impact comparison: Health, Error Rate, P99 Latency, CPU, Memory
 * - Downstream blast radius and secondary failure risk assessments
 * - Autonomy Budget qualification check (auto-executable vs operator approval required)
 * - Safe separation: Dry runs never execute mutating commands; execution requires explicit authorized confirmation
 * - Transparent queueing assumptions, confidence scores, and missing data limitations
 * - Reproducible simulation audit history log
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  simulateDryRun,
  getDryRunHistory,
  getDryRunDetail,
  executeDryRunAction,
} from '../../api/dry_run';
import { useIncidents, useServices } from '../../hooks/useIncidents';
import { useAuth } from '../../context/AuthContext';
import {
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  Activity,
  Cpu,
  Layers,
  Lock,
  Unlock,
  RefreshCw,
  Play,
  Sliders,
  HelpCircle,
  Info,
  ExternalLink,
  FileText,
  Check,
  X,
  Gauge,
  Zap,
  Flame,
  GitFork,
  Radio,
  Network,
  History,
} from 'lucide-react';

const CANDIDATE_ACTIONS_CATALOG = [
  { id: 'SCALE_OUT_PODS', name: 'Scale Out Pods (+100%)', desc: 'Distributes concurrency across more worker replicas' },
  { id: 'RESTART_POD', name: 'Worker Pod Rolling Restart', desc: 'Evicts degraded pods to clear stuck thread pools' },
  { id: 'RATE_LIMIT_TRAFFIC', name: 'Ingress Rate Limiting', desc: 'Sheds 50% ingress traffic at API Gateway' },
  { id: 'ROLLBACK_DEPLOYMENT', name: 'Rollback Deployment', desc: 'Reverts image and config to previous stable revision' },
  { id: 'CIRCUIT_BREAKER_TRIP', name: 'Circuit Breaker Trip', desc: 'Isolates failing dependency and fails fast' },
  { id: 'ADJUST_RETRIES_TIMEOUTS', name: 'Tighten Retries & Timeouts', desc: 'Lowers timeouts to prevent queue pileups' },
  { id: 'FLUSH_REDIS_CACHE', name: 'Flush Redis Cache', desc: 'Invalidates poisoned L2 cache entries' },
];

export default function DryRunTwinView({ preselectedIncident = null, onNavigateToRemediation = null }) {
  const { data: incidentsData } = useIncidents();
  const { data: servicesData } = useServices();
  const { user, canRemediate, openAuthModal } = useAuth();

  const incidents = useMemo(() => (Array.isArray(incidentsData) ? incidentsData : []), [incidentsData]);
  const services = useMemo(() => (Array.isArray(servicesData) ? servicesData : []), [servicesData]);

  // Form State
  const [selectedServiceName, setSelectedServiceName] = useState('payment-service');
  const [selectedIncidentId, setSelectedIncidentId] = useState('');
  const [selectedActions, setSelectedActions] = useState(CANDIDATE_ACTIONS_CATALOG.map((a) => a.id));
  
  // Custom Metrics Override Toggle
  const [overrideMetrics, setOverrideMetrics] = useState(false);
  const [customCpu, setCustomCpu] = useState(85.0);
  const [customMem, setCustomMem] = useState(75.0);
  const [customErrorRate, setCustomErrorRate] = useState(12.0);
  const [customP99, setCustomP99] = useState(650.0);

  // Simulation Results & Loading State
  const [simulating, setSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);
  const [simulationError, setSimulationError] = useState(null);

  // Execution Modal State
  const [executionModalOpen, setExecutionModalOpen] = useState(false);
  const [actionToExecute, setActionToExecute] = useState(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [executingAction, setExecutingAction] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);

  // Audit History State
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [activeTab, setActiveTab] = useState('simulation'); // 'simulation' | 'history'

  // Pre-populate if incoming from another view
  useEffect(() => {
    if (preselectedIncident) {
      setSelectedIncidentId(preselectedIncident.id);
      if (preselectedIncident.service_id) {
        const found = services.find((s) => s.id === preselectedIncident.service_id);
        if (found) setSelectedServiceName(found.service_name || found.name);
      } else if (preselectedIncident.title && preselectedIncident.title.includes('on ')) {
        const extracted = preselectedIncident.title.split('on ')[1].trim();
        if (extracted) setSelectedServiceName(extracted);
      }
    }
  }, [preselectedIncident, services]);

  // Load audit history
  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await getDryRunHistory(25);
      setHistoryList(Array.isArray(res) ? res : (res?.data || []));
    } catch (err) {
      console.warn('Failed to fetch dry-run history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  // Run initial simulation on mount
  useEffect(() => {
    handleRunSimulation();
  }, [selectedServiceName]);

  const handleRunSimulation = async () => {
    setSimulating(true);
    setSimulationError(null);
    setExecutionResult(null);

    try {
      const payload = {
        serviceName: selectedServiceName,
        incidentId: selectedIncidentId || null,
        candidateActions: selectedActions.length > 0 ? selectedActions : null,
        environment: 'production',
        currentMetrics: overrideMetrics
          ? {
              cpu_usage: parseFloat(customCpu),
              memory_usage: parseFloat(customMem),
              error_rate: parseFloat(customErrorRate),
              response_time_p99: parseFloat(customP99),
            }
          : null,
      };

      const res = await simulateDryRun(payload);
      setSimulationResult(res);
      fetchHistory();
    } catch (err) {
      console.error('Dry-run simulation failed:', err);
      setSimulationError(err.message || 'Counterfactual simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  const toggleActionFilter = (actionId) => {
    setSelectedActions((prev) =>
      prev.includes(actionId) ? prev.filter((id) => id !== actionId) : [...prev, actionId]
    );
  };

  const handleOpenExecutionModal = (actionCandidate) => {
    if (!user) {
      openAuthModal();
      return;
    }
    setActionToExecute(actionCandidate);
    setApprovalNotes(`Validated via Dry-Run Twin simulation (${simulationResult?.simulation_id?.slice(0, 8)}). Ready for deployment.`);
    setExecutionModalOpen(true);
  };

  const handleExecuteAction = async () => {
    if (!simulationResult || !actionToExecute) return;
    setExecutingAction(true);
    try {
      const res = await executeDryRunAction({
        simulationId: simulationResult.simulation_id,
        selectedAction: actionToExecute.action,
        approvalNotes: approvalNotes,
      });
      setExecutionResult(res);
      setExecutionModalOpen(false);
      fetchHistory();
    } catch (err) {
      alert(`Execution error: ${err.message}`);
    } finally {
      setExecutingAction(false);
    }
  };

  const recommendedCandidate = useMemo(() => {
    if (!simulationResult?.candidate_simulations) return null;
    return (
      simulationResult.candidate_simulations.find((c) => c.is_recommended) ||
      simulationResult.candidate_simulations[0]
    );
  }, [simulationResult]);

  return (
    <div className="space-y-6 animate-in pb-16">
      {/* =========================================================================
          1. HEADER & STRICT SAFETY SEPARATION BANNER
         ========================================================================= */}
      <div className="glass-card p-6 border-l-4 border-l-synapse-500 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="p-2 rounded-xl bg-gradient-to-tr from-synapse-600 to-indigo-600 text-white shadow-md shadow-synapse-500/20">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </span>
            <h1 className="text-xl font-bold dark:text-white text-slate-900 tracking-tight">
              Dry-Run Twin: Counterfactual Remediation
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Safe Non-Mutating Sandbox
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono dark:bg-slate-800 bg-slate-200 text-slate-400">
              v1.2 Predictive Queueing Twin
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2 max-w-3xl leading-relaxed">
            Evaluates alternative candidate remediations (restarts, scale-outs, rate-limiting, circuit-breaking)
            via queueing theory and dependency topology before touching real systems.
            <strong> Dry runs never execute commands or alter production services.</strong>
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl dark:bg-slate-900/80 bg-slate-200 border dark:border-white/[0.06] border-slate-300 self-start md:self-auto shrink-0">
          <button
            onClick={() => setActiveTab('simulation')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'simulation'
                ? 'bg-synapse-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            Active Simulation
          </button>
          <button
            onClick={() => {
              setActiveTab('history');
              fetchHistory();
            }}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'history'
                ? 'bg-synapse-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Audit History ({historyList.length})
          </button>
        </div>
      </div>

      {activeTab === 'history' ? (
        /* =========================================================================
            AUDIT HISTORY VIEW
           ========================================================================= */
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold dark:text-white text-slate-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-synapse-400" />
              Counterfactual Simulation Audit Records
            </h2>
            <button
              onClick={fetchHistory}
              disabled={loadingHistory}
              className="text-xs px-3 py-1.5 rounded-lg dark:bg-slate-800 bg-slate-200 hover:bg-slate-700 text-slate-300 flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b dark:border-white/[0.06] border-slate-200 text-slate-400">
                  <th className="py-2.5 px-3">Simulation ID</th>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                  <th className="py-2.5 px-3">Target Service</th>
                  <th className="py-2.5 px-3">Recommended Action</th>
                  <th className="py-2.5 px-3">Candidates</th>
                  <th className="py-2.5 px-3">Execution Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-white/[0.04] divide-slate-100">
                {historyList.map((item) => (
                  <tr key={item.id} className="hover:dark:bg-slate-800/40 hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-3 font-mono text-[11px] text-synapse-400">
                      {item.id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-3 font-semibold dark:text-slate-200 text-slate-800">
                      {item.service_name}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono text-[10px]">
                        {item.recommended_action}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{item.candidate_count} evaluated</td>
                    <td className="py-3 px-3">
                      {item.executed_action ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-fit font-bold">
                          <CheckCircle className="w-3 h-3" />
                          Executed ({item.executed_action})
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-500/10 text-slate-400 border border-slate-500/20 font-medium">
                          Simulated Only
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={async () => {
                          try {
                            const res = await getDryRunDetail(item.id);
                            setSimulationResult(res);
                            setSelectedServiceName(res.service_name);
                            setActiveTab('simulation');
                          } catch (err) {
                            alert('Failed to load simulation record: ' + err.message);
                          }
                        }}
                        className="text-xs px-2.5 py-1 rounded bg-synapse-500/10 text-synapse-400 hover:bg-synapse-500/20 font-semibold transition-all"
                      >
                        Replay
                      </button>
                    </td>
                  </tr>
                ))}
                {historyList.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      No simulation records found in audit log.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* =========================================================================
            ACTIVE SIMULATION VIEW
           ========================================================================= */
        <>
          {/* Execution Result Banner if user just dispatched */}
          {executionResult && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between animate-in">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider">Authorized Execution Dispatched</div>
                  <div className="text-xs text-emerald-200/90">{executionResult.message}</div>
                </div>
              </div>
              {executionResult.semaphore_url && (
                <a
                  href={executionResult.semaphore_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-semibold flex items-center gap-1.5 hover:bg-emerald-500 transition-all shrink-0"
                >
                  View Semaphore Playbook <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          )}

          {/* 2. SIMULATION CONTROLS & SELECTION PANEL */}
          <div className="glass-card p-6 space-y-5">
            <div className="flex items-center justify-between border-b dark:border-white/[0.06] border-slate-200 pb-3">
              <h2 className="text-sm font-bold uppercase tracking-wider dark:text-slate-300 text-slate-700 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-synapse-400" />
                Simulation Parameters & Candidate Selection
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setOverrideMetrics(!overrideMetrics)}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                    overrideMetrics
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold'
                      : 'dark:bg-slate-800 bg-slate-100 text-slate-400 border-transparent hover:text-slate-200'
                  }`}
                >
                  {overrideMetrics ? 'Manual Metric Overrides Active' : '+ Metric Overrides'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Target Service Selection */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Target Microservice
                </label>
                <select
                  value={selectedServiceName}
                  onChange={(e) => setSelectedServiceName(e.target.value)}
                  className="w-full text-xs font-mono p-2.5 rounded-xl dark:bg-slate-900 bg-slate-50 border dark:border-white/10 border-slate-300 dark:text-white text-slate-900 focus:ring-2 focus:ring-synapse-500 focus:outline-none"
                >
                  {services.map((svc) => {
                    const name = svc.service_name || svc.name;
                    return (
                      <option key={svc.id || name} value={name}>
                        {name} ({svc.criticality || 'TIER_1'})
                      </option>
                    );
                  })}
                  {services.length === 0 && (
                    <>
                      <option value="payment-service">payment-service (CRITICAL)</option>
                      <option value="auth-service">auth-service (CRITICAL)</option>
                      <option value="order-service">order-service (HIGH)</option>
                      <option value="inventory-service">inventory-service (HIGH)</option>
                      <option value="cart-service">cart-service (HIGH)</option>
                      <option value="catalog-service">catalog-service (HIGH)</option>
                      <option value="notification-service">notification-service (MEDIUM)</option>
                      <option value="recommendation-service">recommendation-service (MEDIUM)</option>
                      <option value="api-gateway">api-gateway (CRITICAL)</option>
                    </>
                  )}
                </select>
              </div>

              {/* Linked Incident Selection (Optional) */}
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                  Associated Incident (Optional)
                </label>
                <select
                  value={selectedIncidentId}
                  onChange={(e) => {
                    setSelectedIncidentId(e.target.value);
                    const inc = incidents.find((i) => i.id === e.target.value);
                    if (inc && inc.service_id) {
                      const matched = services.find((s) => s.id === inc.service_id);
                      if (matched) setSelectedServiceName(matched.service_name || matched.name);
                    }
                  }}
                  className="w-full text-xs p-2.5 rounded-xl dark:bg-slate-900 bg-slate-50 border dark:border-white/10 border-slate-300 dark:text-white text-slate-900 focus:ring-2 focus:ring-synapse-500 focus:outline-none"
                >
                  <option value="">None (Standalone Target Evaluation)</option>
                  {incidents.map((inc) => (
                    <option key={inc.id} value={inc.id}>
                      [{inc.severity}] {inc.title}
                    </option>
                  ))}
                </select>
              </div>

              {/* Simulation Trigger Button */}
              <div className="flex items-end">
                <button
                  onClick={handleRunSimulation}
                  disabled={simulating}
                  className="w-full p-2.5 rounded-xl bg-gradient-to-r from-synapse-600 to-indigo-600 hover:from-synapse-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-synapse-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${simulating ? 'animate-spin' : ''}`} />
                  {simulating ? 'Simulating Counterfactuals...' : 'Run Counterfactual Simulation'}
                </button>
              </div>
            </div>

            {/* Optional Manual Metrics Overrides */}
            {overrideMetrics && (
              <div className="p-4 rounded-xl dark:bg-slate-950/70 bg-amber-500/5 border border-amber-500/20 grid grid-cols-2 sm:grid-cols-4 gap-4 animate-in">
                <div>
                  <label className="text-[11px] text-slate-400 font-semibold block mb-1">CPU Usage ({customCpu}%)</label>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={customCpu}
                    onChange={(e) => setCustomCpu(e.target.value)}
                    className="w-full accent-amber-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 font-semibold block mb-1">Memory Usage ({customMem}%)</label>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={customMem}
                    onChange={(e) => setCustomMem(e.target.value)}
                    className="w-full accent-amber-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 font-semibold block mb-1">Error Rate ({customErrorRate}%)</label>
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="0.5"
                    value={customErrorRate}
                    onChange={(e) => setCustomErrorRate(e.target.value)}
                    className="w-full accent-rose-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 font-semibold block mb-1">P99 Latency ({customP99}ms)</label>
                  <input
                    type="range"
                    min="20"
                    max="3000"
                    step="50"
                    value={customP99}
                    onChange={(e) => setCustomP99(e.target.value)}
                    className="w-full accent-indigo-500"
                  />
                </div>
              </div>
            )}

            {/* Candidate Action Toggles */}
            <div>
              <div className="text-xs font-semibold text-slate-400 mb-2">
                Candidate Remediations to Evaluate in Twin ({selectedActions.length}/{CANDIDATE_ACTIONS_CATALOG.length}):
              </div>
              <div className="flex flex-wrap gap-2">
                {CANDIDATE_ACTIONS_CATALOG.map((item) => {
                  const active = selectedActions.includes(item.id);
                  return (
                    <button
                      key={item.id}
                      onClick={() => toggleActionFilter(item.id)}
                      className={`text-xs px-3 py-1.5 rounded-lg border flex items-center gap-1.5 transition-all ${
                        active
                          ? 'bg-synapse-500/15 border-synapse-500/40 text-synapse-300 font-semibold'
                          : 'dark:bg-slate-900 bg-slate-100 dark:border-white/5 border-slate-200 text-slate-500 hover:text-slate-300'
                      }`}
                    >
                      <span className={`w-2 h-2 rounded-full ${active ? 'bg-synapse-400' : 'bg-slate-600'}`} />
                      {item.name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Error Message */}
          {simulationError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{simulationError}</span>
            </div>
          )}

          {/* 3. BASELINE PRE-REMEDIATION SNAPSHOT */}
          {simulationResult && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="glass-card p-3.5 border-l-2 border-l-slate-400">
                <div className="text-[10px] uppercase font-bold text-slate-400">Current Health</div>
                <div className="text-xl font-bold dark:text-white text-slate-900 mt-0.5">
                  {simulationResult.baseline_telemetry?.health_score}%
                </div>
                <div className="text-[10px] text-slate-500">Pre-remediation state</div>
              </div>
              <div className="glass-card p-3.5 border-l-2 border-l-rose-500">
                <div className="text-[10px] uppercase font-bold text-rose-400">Baseline Risk</div>
                <div className="text-xl font-bold text-rose-400 mt-0.5">
                  {simulationResult.baseline_telemetry?.risk_score}%
                </div>
                <div className="text-[10px] text-slate-500">{simulationResult.baseline_telemetry?.status}</div>
              </div>
              <div className="glass-card p-3.5 border-l-2 border-l-amber-500">
                <div className="text-[10px] uppercase font-bold text-amber-400">Error Rate</div>
                <div className="text-xl font-bold text-amber-300 mt-0.5">
                  {simulationResult.baseline_telemetry?.error_rate_percent}%
                </div>
                <div className="text-[10px] text-slate-500">Active ingress faults</div>
              </div>
              <div className="glass-card p-3.5 border-l-2 border-l-indigo-500">
                <div className="text-[10px] uppercase font-bold text-indigo-400">P99 Latency</div>
                <div className="text-xl font-bold text-indigo-300 mt-0.5">
                  {simulationResult.baseline_telemetry?.response_time_p99_ms}ms
                </div>
                <div className="text-[10px] text-slate-500">SLA threshold: 200ms</div>
              </div>
              <div className="glass-card p-3.5 border-l-2 border-l-purple-500">
                <div className="text-[10px] uppercase font-bold text-purple-400">CPU Load</div>
                <div className="text-xl font-bold text-purple-300 mt-0.5">
                  {simulationResult.baseline_telemetry?.cpu_usage_percent}%
                </div>
                <div className="text-[10px] text-slate-500">Memory: {simulationResult.baseline_telemetry?.memory_usage_percent}%</div>
              </div>
              <div className="glass-card p-3.5 border-l-2 border-l-emerald-500">
                <div className="text-[10px] uppercase font-bold text-emerald-400">Active Simulation</div>
                <div className="text-xs font-mono font-bold dark:text-emerald-300 text-emerald-600 mt-1 truncate">
                  {simulationResult.simulation_id.slice(0, 8)}
                </div>
                <div className="text-[10px] text-slate-500">{simulationResult.candidate_simulations?.length} candidates</div>
              </div>
            </div>
          )}

          {/* 4. RECOMMENDED ACTION SPOTLIGHT CARD */}
          {recommendedCandidate && (
            <div className="glass-card p-6 border-2 border-synapse-500/60 bg-gradient-to-br from-synapse-500/10 via-indigo-500/5 to-purple-500/10 shadow-xl shadow-synapse-500/10 relative overflow-hidden">
              <div className="absolute top-0 right-0 px-4 py-1.5 rounded-bl-xl bg-gradient-to-r from-synapse-600 to-indigo-600 text-white text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 shadow-md">
                <Sparkles className="w-3.5 h-3.5" />
                Safest Recommended Action
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-3">
                  <div>
                    <span className="text-xs font-mono text-synapse-400 font-bold uppercase tracking-wider">
                      Optimal Remediation Choice
                    </span>
                    <h3 className="text-xl font-black dark:text-white text-slate-900 mt-0.5">
                      {recommendedCandidate.name}
                    </h3>
                    <p className="text-xs text-slate-300 mt-1">{recommendedCandidate.description}</p>
                  </div>

                  <p className="text-xs text-slate-200 dark:text-slate-300 bg-white/5 dark:bg-black/20 p-3 rounded-xl border border-white/10 leading-relaxed font-sans">
                    💡 <strong>Justification:</strong> {recommendedCandidate.recommendation_reason}
                  </p>

                  <div className="flex flex-wrap items-center gap-3 pt-1">
                    <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${
                      recommendedCandidate.can_auto_execute
                        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                        : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                    }`}>
                      {recommendedCandidate.can_auto_execute ? (
                        <>
                          <CheckCircle className="w-3.5 h-3.5" />
                          Autonomy Budget: Cleared for Auto-Execution
                        </>
                      ) : (
                        <>
                          <Lock className="w-3.5 h-3.5" />
                          Autonomy Policy: Human Approval Gate Required
                        </>
                      )}
                    </span>

                    <span className="text-xs font-mono px-2.5 py-1 rounded-lg dark:bg-slate-900 bg-slate-200 text-slate-300 border dark:border-white/10 border-slate-300">
                      Reversibility: <strong>{recommendedCandidate.reversibility}</strong>
                    </span>

                    <span className="text-xs px-2.5 py-1 rounded-lg bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                      Confidence: <strong>{Math.round(recommendedCandidate.confidence_score * 100)}%</strong> ({recommendedCandidate.uncertainty_tier} Uncertainty)
                    </span>
                  </div>
                </div>

                {/* Score & Action Column */}
                <div className="flex flex-col justify-between items-center lg:items-end border-t lg:border-t-0 lg:border-l dark:border-white/10 border-slate-200 pt-4 lg:pt-0 lg:pl-6 space-y-4">
                  <div className="text-center lg:text-right">
                    <div className="text-[10px] uppercase font-bold text-slate-400">Composite Efficacy Score</div>
                    <div className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-synapse-400 via-indigo-400 to-purple-400">
                      {recommendedCandidate.efficacy_score}
                      <span className="text-sm text-slate-400 font-normal">/100</span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Est. Recovery: <strong>{recommendedCandidate.estimated_recovery_seconds}s</strong>
                    </div>
                  </div>

                  <button
                    onClick={() => handleOpenExecutionModal(recommendedCandidate)}
                    className="w-full lg:w-auto px-5 py-2.5 rounded-xl bg-gradient-to-r from-synapse-600 to-emerald-600 hover:from-synapse-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg shadow-synapse-500/30 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    Authorize & Execute Plan
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 5. SIDE-BY-SIDE CANDIDATE COMPARISON MATRIX */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider dark:text-slate-300 text-slate-700 flex items-center gap-2">
                <Layers className="w-4 h-4 text-synapse-400" />
                Side-by-Side Candidate Remediations ({simulationResult?.candidate_simulations?.length || 0})
              </h3>
              <span className="text-xs text-slate-400">
                Sorted by predicted recovery efficacy & risk reduction
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {simulationResult?.candidate_simulations?.map((candidate) => {
                const isRec = candidate.is_recommended;
                return (
                  <div
                    key={candidate.action}
                    className={`glass-card p-5 flex flex-col justify-between space-y-4 transition-all hover:border-synapse-500/50 ${
                      isRec
                        ? 'ring-2 ring-synapse-500/60 dark:bg-slate-900/90 bg-white'
                        : 'dark:bg-slate-900/60 bg-white'
                    }`}
                  >
                    {/* Header */}
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">
                          {candidate.action}
                        </span>
                        {isRec && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-synapse-500/20 text-synapse-300 border border-synapse-500/40">
                            ★ RECOMMENDED
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-bold dark:text-white text-slate-900 mt-2">
                        {candidate.name}
                      </h4>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {candidate.description}
                      </p>
                    </div>

                    {/* Metrics Grid */}
                    <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y dark:border-white/[0.06] border-slate-200">
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Predicted Health</span>
                        <div className="font-bold text-emerald-400 flex items-center gap-1">
                          {candidate.predicted_health_score}%
                          <span className="text-[10px] text-emerald-500 font-normal">
                            (+{candidate.health_delta}%)
                          </span>
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Predicted Risk</span>
                        <div className="font-bold text-indigo-400 flex items-center gap-1">
                          {candidate.predicted_risk_score}%
                          <span className="text-[10px] text-indigo-300 font-normal">
                            (-{candidate.risk_delta} pts)
                          </span>
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Residual Errors</span>
                        <div className="font-semibold text-slate-300">
                          {candidate.predicted_error_rate}%
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">P99 Response</span>
                        <div className="font-semibold text-slate-300">
                          {candidate.predicted_p99_latency_ms}ms
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Est. Recovery</span>
                        <div className="font-semibold text-slate-300">
                          {candidate.estimated_recovery_seconds}s
                        </div>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Blast Radius</span>
                        <div className={`font-semibold ${
                          candidate.blast_radius_tier === 'LOW' ? 'text-emerald-400' : 'text-amber-400'
                        }`}>
                          {candidate.blast_radius_tier}
                        </div>
                      </div>
                    </div>

                    {/* Secondary Hazards Warning Box */}
                    {candidate.secondary_failure_risks?.length > 0 ? (
                      <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11px] space-y-1">
                        <div className="font-bold flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          Secondary Hazard ({Math.round(candidate.secondary_failure_probability * 100)}% prob):
                        </div>
                        <div className="text-amber-200/90 text-[10px] leading-snug">
                          {candidate.secondary_failure_risks[0].risk_type.replace(/_/g, ' ')} on {candidate.secondary_failure_risks[0].target_component}
                        </div>
                        <div className="text-[10px] text-slate-400 italic">
                          💡 {candidate.secondary_failure_risks[0].mitigation_hint}
                        </div>
                      </div>
                    ) : (
                      <div className="p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 text-[11px] flex items-center gap-1.5">
                        <CheckCircle className="w-3 h-3" />
                        No significant secondary failure hazard predicted.
                      </div>
                    )}

                    {/* Footer / Autonomy Check & Action */}
                    <div className="pt-2 flex items-center justify-between gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        candidate.can_auto_execute
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {candidate.can_auto_execute ? 'Auto-Executable' : 'Requires Approval'}
                      </span>

                      <button
                        onClick={() => handleOpenExecutionModal(candidate)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-synapse-500/15 hover:bg-synapse-500/25 text-synapse-300 font-semibold border border-synapse-500/30 flex items-center gap-1 transition-all"
                      >
                        Execute <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 6. TRANSPARENT ASSUMPTIONS & LIMITATIONS PANEL */}
          {simulationResult && (
            <div className="glass-card p-6 border dark:border-white/[0.06] border-slate-200 space-y-4">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
                <Info className="w-4 h-4 text-synapse-400" />
                Predictive Twin Assumptions, Evidence & Limitations
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-400 leading-relaxed">
                <div className="space-y-2">
                  <div className="font-semibold text-slate-200">Simulation Model Assumptions:</div>
                  <ul className="list-disc pl-4 space-y-1">
                    {simulationResult.assumptions?.map((assump, idx) => (
                      <li key={idx}>{assump}</li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-2">
                  <div className="font-semibold text-slate-200">Limitations & Uncertainty Boundaries:</div>
                  <ul className="list-disc pl-4 space-y-1 text-amber-300/80">
                    {simulationResult.limitations?.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                    {(!simulationResult.limitations || simulationResult.limitations.length === 0) && (
                      <li>Sufficient historical sample depth available for calibrated services.</li>
                    )}
                  </ul>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border dark:border-white/5 border-slate-200 text-[11px] text-slate-400 italic">
                ⚠️ <strong>Simulator Disclaimer:</strong> {simulationResult.disclaimer}
              </div>
            </div>
          )}
        </>
      )}

      {/* =========================================================================
          7. SEPARATE AUTHORIZED EXECUTION CONFIRMATION MODAL
         ========================================================================= */}
      {executionModalOpen && actionToExecute && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in">
          <div className="glass-card p-6 max-w-lg w-full space-y-5 border-synapse-500/40 shadow-2xl">
            <div className="flex items-center justify-between border-b dark:border-white/10 border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-synapse-600 text-white">
                  <Play className="w-4 h-4 fill-current" />
                </span>
                <h3 className="text-base font-bold dark:text-white text-slate-900">
                  Authorize Remediation Execution
                </h3>
              </div>
              <button
                onClick={() => setExecutionModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl dark:bg-slate-900 bg-slate-100 border dark:border-white/5 border-slate-200 space-y-1.5">
                <div className="text-slate-400">Target Microservice:</div>
                <div className="font-bold dark:text-white text-slate-900 text-sm">
                  {selectedServiceName}
                </div>
                <div className="text-slate-400 mt-2">Remediation Action:</div>
                <div className="font-bold text-synapse-400 text-sm">
                  {actionToExecute.name} ({actionToExecute.action})
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300">
                <div className="font-bold flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  Explicit Separation Confirmation
                </div>
                <p className="mt-1 text-[11px] text-amber-200/90 leading-relaxed">
                  You are transitioning from the Dry-Run Simulation sandbox to actual production execution.
                  This will trigger the verified Ansible Semaphore playbook on the live target service.
                </p>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Operator Authorization & Audit Notes:
                </label>
                <textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  rows={2}
                  className="w-full text-xs p-2.5 rounded-xl dark:bg-slate-900 bg-slate-50 border dark:border-white/10 border-slate-300 dark:text-white text-slate-900 focus:ring-2 focus:ring-synapse-500 focus:outline-none"
                  placeholder="Reason for execution, incident ticket reference, or approval authorization..."
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setExecutionModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteAction}
                disabled={executingAction}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-synapse-600 to-emerald-600 hover:from-synapse-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg flex items-center gap-2 disabled:opacity-50"
              >
                {executingAction ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Dispatching Playbook...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Confirm & Execute Real Action
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
