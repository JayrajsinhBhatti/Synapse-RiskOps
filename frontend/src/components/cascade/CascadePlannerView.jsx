/**
 * frontend/src/components/cascade/CascadePlannerView.jsx
 * 
 * Cascade Interception Planner Console for Synapse RiskOps.
 * 
 * Capabilities:
 * - Simulates failure propagation across the NetworkX service dependency graph
 * - Visualizes propagation wave: Seed Fault -> Direct Callers -> Secondary Callers
 * - Formulates, ranks, and compares competing protective interception plans
 * - Computes before vs after blast-radius reduction and protected services
 * - Enforces Autonomy Budget governance: low-risk auto-execution vs critical operator sign-off
 * - Safely dispatches playbooks via Ansible Semaphore with tamper-evident audit logging
 * - Evidence-based predictions with explicit topological assumptions
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useServices } from '../../hooks/useIncidents';
import { simulateCascade, executeInterceptionPlan } from '../../api/cascade';
import {
  GitFork,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  Activity,
  Layers,
  Server,
  ArrowRight,
  TrendingDown,
  Info,
  Sliders,
  Check,
  AlertOctagon,
  Lock,
  Sparkles,
} from 'lucide-react';

const FAILURE_TYPES = [
  { id: 'latency_spike', label: 'Latency Spike (p99 > 3500ms)', desc: 'Synchronous thread pool starvation & caller timeouts' },
  { id: 'error_storm', label: 'Error Storm (5xx > 40%)', desc: 'Retry storm amplification exhausting connection pools' },
  { id: 'memory_exhaustion', label: 'Memory Leak (OOM Kill Warning)', desc: 'Worker node heap pressure and container restarts' },
  { id: 'connection_pool_saturation', label: 'DB Connection Saturation', desc: 'Blocked SQL connection threads choking transactions' },
  { id: 'service_crash', label: 'Hard Crash / Network Partition', desc: 'Immediate failover panic and traffic redirection waves' },
];

export default function CascadePlannerView() {
  const { user, role } = useAuth();
  const { data: servicesData } = useServices();

  const services = useMemo(() => (Array.isArray(servicesData) ? servicesData : []), [servicesData]);

  // Simulation Controls
  const [seedService, setSeedService] = useState('payment-service');
  const [failureType, setFailureType] = useState('latency_spike');
  const [severity, setSeverity] = useState(0.85);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationData, setSimulationData] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [showShieldedView, setShowShieldedView] = useState(true);
  const [errorNotice, setErrorNotice] = useState(null);

  // Execution Modal & Status
  const [isExecModalOpen, setIsExecModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);

  // Auto-simulate on initial mount
  useEffect(() => {
    handleRunSimulation();
  }, []);

  const handleRunSimulation = async (targetSeed = seedService, targetType = failureType, targetSev = severity) => {
    setIsSimulating(true);
    setErrorNotice(null);
    setExecResult(null);
    try {
      const data = await simulateCascade({
        seedService: targetSeed,
        failureType: targetType,
        severity: targetSev,
      });
      setSimulationData(data);
      if (data?.recommended_plan) {
        setSelectedPlanId(data.recommended_plan.plan_id);
      } else if (data?.candidate_plans?.length > 0) {
        setSelectedPlanId(data.candidate_plans[0].plan_id);
      }
    } catch (err) {
      console.error('Simulation error:', err);
      setErrorNotice(err.message || 'Failed to simulate cascade propagation.');
    } finally {
      setIsSimulating(false);
    }
  };

  const activePlan = useMemo(() => {
    if (!simulationData?.candidate_plans) return null;
    return simulationData.candidate_plans.find((p) => p.plan_id === selectedPlanId) || simulationData.recommended_plan;
  }, [simulationData, selectedPlanId]);

  const isOperatorOrAdmin = role === 'ADMIN' || role === 'OPERATOR';

  const handleExecutePlan = async () => {
    if (!activePlan) return;
    setIsExecuting(true);
    setErrorNotice(null);
    try {
      const res = await executeInterceptionPlan({
        planId: activePlan.plan_id,
        seedService: simulationData.seed_service,
        strategy: activePlan.strategy,
        approvalNotes: approvalNotes || `Cascade Interception authorized by ${user?.username || 'Operator'}`,
      });
      setExecResult(res);
      setIsExecModalOpen(false);
    } catch (err) {
      setErrorNotice(err.message || 'Interception execution failed.');
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-500 dark:text-indigo-400">
              <GitFork className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                Cascade Interception Planner
                <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 border border-indigo-500/20 dark:border-indigo-500/30">
                  NetworkX AI Engine
                </span>
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Simulate failure propagation across service topology, evaluate competing interception plans, and enforce Autonomy Budget safeguards.
              </p>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleRunSimulation()}
            disabled={isSimulating}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            {isSimulating ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                <span>Simulating Graph Waves...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 text-amber-300" />
                <span>Re-Simulate Cascade</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {errorNotice && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 flex items-start gap-3">
          <AlertOctagon className="w-5 h-5 text-rose-500 dark:text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs flex-1">
            <span className="font-semibold">Notice:</span> {errorNotice}
          </div>
          <button onClick={() => setErrorNotice(null)} className="text-rose-500 hover:text-rose-700 dark:text-rose-400 dark:hover:text-white text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Execution Success Toast */}
      {execResult && (
        <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-500 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Interception Plan Dispatched Safely</h4>
              <p className="text-xs text-emerald-700 dark:text-emerald-200/90">{execResult.message}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {execResult.dispatched_actions?.map((act, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-500/30 font-mono text-[11px] text-emerald-800 dark:text-emerald-300">
                    {act}
                  </span>
                ))}
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 font-mono">
                Audit Record ID: {execResult.audit_log_ids?.[0] || 'Confirmed'} • Execution Time: {execResult.execution_duration_seconds}s
              </p>
            </div>
          </div>
          <button onClick={() => setExecResult(null)} className="text-emerald-600 dark:text-emerald-400 hover:text-slate-900 dark:hover:text-white text-xs">
            ✕
          </button>
        </div>
      )}

      {/* Simulation Scenario Controls */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-2 mb-4 text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
          <Sliders className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
          <span>Failure Injection Parameters</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Seed Service Dropdown */}
          <div>
            <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1.5">
              Primary Seed Service (Failing Source)
            </label>
            <select
              value={seedService}
              onChange={(e) => {
                setSeedService(e.target.value);
                handleRunSimulation(e.target.value, failureType, severity);
              }}
              className="w-full bg-slate-50 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              {(services.length > 0 ? services : [
                { service_name: 'payment-service', criticality: 'CRITICAL' },
                { service_name: 'order-service', criticality: 'HIGH' },
                { service_name: 'cart-service', criticality: 'HIGH' },
                { service_name: 'catalog-service', criticality: 'HIGH' },
                { service_name: 'inventory-service', criticality: 'HIGH' },
                { service_name: 'auth-service', criticality: 'CRITICAL' },
                { service_name: 'api-gateway', criticality: 'CRITICAL' },
                { service_name: 'postgres-primary', criticality: 'CRITICAL' },
              ]).map((s) => {
                const name = s.service_name || s.name;
                return (
                  <option key={name} value={name}>
                    {name} ({s.criticality || 'SERVICE'})
                  </option>
                );
              })}
            </select>
          </div>

          {/* Failure Type */}
          <div>
            <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1.5">
              Failure Propagation Mode
            </label>
            <select
              value={failureType}
              onChange={(e) => {
                setFailureType(e.target.value);
                handleRunSimulation(seedService, e.target.value, severity);
              }}
              className="w-full bg-slate-50 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              {FAILURE_TYPES.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          {/* Severity Slider */}
          <div>
            <div className="flex justify-between text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1.5">
              <span>Failure Severity Magnitude</span>
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">{Math.round(severity * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.2"
              max="1.0"
              step="0.05"
              value={severity}
              onChange={(e) => setSeverity(parseFloat(e.target.value))}
              onMouseUp={() => handleRunSimulation(seedService, failureType, severity)}
              onTouchEnd={() => handleRunSimulation(seedService, failureType, severity)}
              className="w-full accent-indigo-500 cursor-pointer h-2 bg-slate-200 dark:bg-slate-800 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>Mild Saturation</span>
              <span>Total Cascade Failure</span>
            </div>
          </div>
        </div>
      </div>

      {/* Impact Overview KPIs */}
      {simulationData && activePlan && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Baseline Blast Radius */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-rose-500/20 shadow-sm relative overflow-hidden">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Baseline Blast Radius</span>
              <ShieldAlert className="w-4 h-4 text-rose-500 dark:text-rose-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-rose-500 dark:text-rose-400 font-mono">
                {simulationData.simulation.blast_radius_percent}%
              </span>
              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                ({simulationData.simulation.at_risk_count} services at risk)
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div
                className="bg-rose-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${simulationData.simulation.blast_radius_percent}%` }}
              />
            </div>
          </div>

          {/* Intercepted Blast Radius */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-emerald-500/20 shadow-sm relative overflow-hidden">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Post-Interception Radius</span>
              <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-emerald-500 dark:text-emerald-400 font-mono">
                {activePlan.blast_radius_after_percent}%
              </span>
              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                ({activePlan.services_at_risk_after} residual)
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${activePlan.blast_radius_after_percent}%` }}
              />
            </div>
          </div>

          {/* Net Mitigation Delta */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-indigo-500/20 shadow-sm">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Blast Radius Mitigated</span>
              <TrendingDown className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-indigo-600 dark:text-indigo-300 font-mono">
                -{activePlan.blast_radius_reduction_percent}%
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                +{activePlan.services_protected_count} shielded
              </span>
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-3 flex items-center gap-1 font-mono">
              <span>Efficacy Score:</span>
              <span className="text-slate-900 dark:text-white font-bold">{activePlan.overall_efficacy_score}/100</span>
            </div>
          </div>

          {/* Autonomy Budget Governance */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-purple-500/20 shadow-sm">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Autonomy Budget Tier</span>
              {activePlan.requires_human_approval ? (
                <Lock className="w-4 h-4 text-amber-500 dark:text-amber-400" />
              ) : (
                <Zap className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              )}
            </div>
            <div className="mt-1">
              <span
                className={`inline-block px-2.5 py-1 rounded-md text-[11px] font-bold font-mono ${
                  activePlan.requires_human_approval
                    ? 'bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                    : 'bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30'
                }`}
              >
                {activePlan.autonomy_tier}
              </span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 truncate">
              {activePlan.requires_human_approval ? 'Requires Operator Sign-off' : 'Authorized for Safe Auto-Run'}
            </p>
          </div>
        </div>
      )}

      {/* Interactive Topology Propagation & Shielding Wave */}
      {simulationData && (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                <span>Cascade Propagation Wave & Shielding Points</span>
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Visualizing failure transmission through caller dependencies (predecessors) and downstream services.
              </p>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-900/90 p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-xs">
              <button
                onClick={() => setShowShieldedView(false)}
                className={`px-3 py-1 rounded font-medium transition-all ${
                  !showShieldedView ? 'bg-rose-500/20 text-rose-700 dark:text-rose-300 font-bold border border-rose-500/30' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                Unmitigated Cascade
              </button>
              <button
                onClick={() => setShowShieldedView(true)}
                className={`px-3 py-1 rounded font-medium transition-all ${
                  showShieldedView ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-bold border border-emerald-500/30' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                Shielded Plan Preview
              </button>
            </div>
          </div>

          {/* Interactive Node Wave Chain */}
          <div className="overflow-x-auto pb-4">
            <div className="flex items-stretch gap-4 min-w-[700px]">
              {simulationData.simulation.propagation_timeline?.map((hop, idx) => {
                const isSeed = hop.is_seed;
                const isProtected = showShieldedView && activePlan?.protected_services_list?.includes(hop.service_name);
                const isResidual = showShieldedView && activePlan?.residual_at_risk_services?.includes(hop.service_name);

                return (
                  <React.Fragment key={hop.service_name}>
                    {idx > 0 && (
                      <div className="flex flex-col items-center justify-center text-slate-400 dark:text-slate-600 px-1">
                        <ArrowRight className="w-5 h-5 text-slate-400 dark:text-slate-500" />
                        <span className="text-[9px] font-mono text-slate-500 dark:text-slate-400">+{hop.estimated_time_to_impact_seconds}s</span>
                      </div>
                    )}

                    <div
                      className={`flex-1 rounded-xl p-4 transition-all border ${
                        isSeed
                          ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-500/60 shadow-lg'
                          : isProtected
                          ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-500/50 shadow-md'
                          : isResidual
                          ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-500/40'
                          : 'bg-slate-50 dark:bg-slate-900/80 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      {/* Node Header */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                          {isSeed ? 'ROOT FAULT' : `HOP ${hop.depth}`}
                        </span>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                            hop.criticality === 'CRITICAL'
                              ? 'bg-rose-500/10 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300 border border-rose-500/30'
                              : 'bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {hop.criticality}
                        </span>
                      </div>

                      {/* Service Name */}
                      <div className="font-bold text-sm text-slate-900 dark:text-white truncate mb-1">
                        {hop.service_name}
                      </div>

                      {/* Status Badge */}
                      <div className="mb-3">
                        {isSeed ? (
                          <span className="text-[10px] font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                            Seed Failure
                          </span>
                        ) : isProtected ? (
                          <span className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Shielded by Plan
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            At Risk ({Math.round(hop.propagation_probability * 100)}%)
                          </span>
                        )}
                      </div>

                      {/* Transmission Mechanism & Time */}
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-2 space-y-1">
                        <div>
                          <span className="text-slate-400 dark:text-slate-500">Mechanism:</span>{' '}
                          <span className="text-slate-700 dark:text-slate-300">{hop.impact_mechanism}</span>
                        </div>
                        {!isSeed && (
                          <div>
                            <span className="text-slate-400 dark:text-slate-500">Est. Impact:</span>{' '}
                            <span className="font-mono text-indigo-600 dark:text-indigo-300">{hop.estimated_time_to_impact_seconds}s</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Evidence and Assumptions Note */}
          <div className="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-indigo-500 dark:text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-800 dark:text-slate-200">Evidence-Based Assumptions:</span>{' '}
              {simulationData.simulation.assumptions_and_evidence?.join(' • ')}
            </div>
          </div>
        </div>
      )}

      {/* Candidate Interception Plans Ranking & Comparison */}
      {simulationData?.candidate_plans && (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Shield className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                <span>Ranked Interception Action Plans</span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Evaluated against blast-radius mitigation, traffic disruption, execution speed, and Autonomy Budget risk.
              </p>
            </div>

            {activePlan && (
              <button
                onClick={() => setIsExecModalOpen(true)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-600/30 flex items-center gap-2"
              >
                <Play className="w-4 h-4 fill-white" />
                <span>Dispatch Active Plan ({activePlan.name})</span>
              </button>
            )}
          </div>

          {/* Plans Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {simulationData.candidate_plans.map((plan) => {
              const isSelected = selectedPlanId === plan.plan_id;
              const isRecommended = plan.is_recommended;

              return (
                <div
                  key={plan.plan_id}
                  onClick={() => setSelectedPlanId(plan.plan_id)}
                  className={`rounded-2xl p-5 border transition-all cursor-pointer relative overflow-hidden ${
                    isSelected
                      ? 'bg-indigo-50/40 dark:bg-slate-900/90 border-indigo-500 ring-2 ring-indigo-500/30 shadow-xl'
                      : 'bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  {/* Top Badges */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                        Rank #{plan.rank}
                      </span>
                      {isRecommended && (
                        <span className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                          <Sparkles className="w-3 h-3 text-amber-500 dark:text-amber-300" />
                          Recommended Best Plan
                        </span>
                      )}
                    </div>

                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                        plan.requires_human_approval
                          ? 'bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {plan.autonomy_tier}
                    </span>
                  </div>

                  {/* Plan Name & Strategy */}
                  <h4 className="text-base font-bold text-slate-900 dark:text-white mb-1.5 flex items-center justify-between">
                    <span>{plan.name}</span>
                    {isSelected && <Check className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />}
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-300/90 mb-4">{plan.architectural_rationale}</p>

                  {/* Before vs After Impact Comparison */}
                  <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-white dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 mb-4 text-center">
                    <div>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 block">Radius Before</span>
                      <span className="text-xs font-bold font-mono text-rose-500 dark:text-rose-400">{plan.blast_radius_before_percent}%</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 block">Radius After</span>
                      <span className="text-xs font-bold font-mono text-emerald-600 dark:text-emerald-400">{plan.blast_radius_after_percent}%</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 block">Net Reduction</span>
                      <span className="text-xs font-bold font-mono text-indigo-600 dark:text-indigo-300">-{plan.blast_radius_reduction_percent}%</span>
                    </div>
                  </div>

                  {/* Actions Breakdown */}
                  <div className="space-y-2 mb-4">
                    <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                      Candidate Interception Actions ({plan.actions.length}):
                    </span>
                    {plan.actions.map((act, aIdx) => (
                      <div
                        key={aIdx}
                        className="text-xs p-2.5 rounded-lg bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 flex items-start gap-2.5 shadow-xs"
                      >
                        <Zap className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400 shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-800 dark:text-slate-200">
                              {act.action_type} → <span className="text-indigo-600 dark:text-indigo-300">{act.target_service}</span>
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">{act.reversibility}</span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{act.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Key Metrics Footnote */}
                  <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-3">
                    <div className="flex items-center gap-3">
                      <span>
                        Disruption: <strong className="text-slate-900 dark:text-white">{plan.disruption_level}</strong>
                      </span>
                      <span>
                        Est. Recovery: <strong className="text-slate-900 dark:text-white font-mono">{plan.estimated_total_recovery_seconds}s</strong>
                      </span>
                    </div>
                    <div className="text-indigo-600 dark:text-indigo-400 font-medium">
                      Protected: {plan.services_protected_count} services
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Execution Confirmation Modal */}
      {isExecModalOpen && activePlan && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 max-w-lg w-full border border-slate-200 dark:border-slate-700 shadow-2xl space-y-4 animate-in">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">Execute Cascade Interception Plan</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">{activePlan.name}</p>
                </div>
              </div>
              <button
                onClick={() => setIsExecModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Governance Gate Notice */}
            <div
              className={`p-3.5 rounded-xl border text-xs ${
                activePlan.requires_human_approval
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-200'
                  : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-200'
              }`}
            >
              <div className="flex items-center gap-2 font-semibold mb-1">
                {activePlan.requires_human_approval ? (
                  <>
                    <Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <span>Autonomy Budget: Operator Sign-off Required</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Autonomy Budget: Safe Auto-Execution Cleared</span>
                  </>
                )}
              </div>
              <p className="text-[11px] opacity-90">{activePlan.governance_reasoning}</p>
            </div>

            {/* Sign-off notes */}
            <div>
              <label className="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Audit Approval Notes / Operator Authorization
              </label>
              <textarea
                rows="3"
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="e.g. Authorized by Incident Commander. Immediate circuit breaker trip to protect downstream checkout."
                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-2.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Actions summary */}
            <div className="bg-slate-50 dark:bg-slate-950/70 p-3 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
              <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">Actions to Dispatch:</span>
              <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400 text-[11px]">
                {activePlan.actions.map((a, i) => (
                  <li key={i}>
                    {a.action_type} on <span className="text-slate-900 dark:text-white font-mono font-medium">{a.target_service}</span> (disruption: {a.disruption_score}%)
                  </li>
                ))}
              </ul>
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setIsExecModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleExecutePlan}
                disabled={isExecuting}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-600/30 flex items-center gap-2 disabled:opacity-50"
              >
                {isExecuting ? (
                  <>
                    <RotateCcw className="w-4 h-4 animate-spin" />
                    <span>Dispatching Runbooks...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Authorize & Dispatch</span>
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
