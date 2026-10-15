/**
 * frontend/src/components/causal/CausalGraphView.jsx
 * Synapse RiskOps - Chaos-Calibrated Causal Graph Console
 *
 * Visualizes the experimentally calibrated dependency graph with:
 * - Edge color and style distinguishing VALIDATED_CAUSAL, OBSERVED, DECLARED, and UNCERTAIN
 * - Edge thickness proportional to causal strength and badges for propagation delay tau
 * - Interactive Edge Evidence Inspector modal with DiD effect sizes and supporting experiments
 * - Controlled Chaos Calibration Runner with bounded intensity and guaranteed auto-rollback
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Network,
  Flame,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Activity,
  ArrowRight,
  Play,
  RefreshCw,
  Clock,
  Filter,
  Eye,
  Info,
  X,
  Shield,
  Layers,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

import {
  fetchCausalGraph,
  runCausalExperiment,
  fetchEdgeEvidence,
  seedBaselineCalibrations,
} from '../../api/causal';

/**
 * Custom Node for Causal Graph
 */
function CausalServiceNode({ data }) {
  const { label, tier, criticality, owner, isTarget, isControl } = data;

  return (
    <div
      className={`px-3 py-2.5 rounded-xl border transition-all duration-300 min-w-[170px] shadow-lg backdrop-blur-md ${
        isTarget
          ? 'bg-red-950/90 border-red-500 shadow-red-500/40 ring-2 ring-red-400 animate-pulse text-white'
          : isControl
          ? 'bg-blue-950/80 border-blue-400 shadow-blue-500/30 ring-1 ring-blue-400 text-white'
          : 'dark:bg-slate-900/90 bg-white/95 dark:border-slate-700/80 border-slate-200 hover:border-slate-400 dark:hover:border-slate-500'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-indigo-400 !w-2 !h-2" />

      <div className="flex items-center justify-between mb-1.5">
        <span
          className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
            tier === 1
              ? 'dark:bg-indigo-500/30 bg-indigo-50 dark:text-indigo-300 text-indigo-700 border dark:border-indigo-500/40 border-indigo-200'
              : tier === 2
              ? 'dark:bg-cyan-500/30 bg-cyan-50 dark:text-cyan-300 text-cyan-700 border dark:border-cyan-500/40 border-cyan-200'
              : 'dark:bg-slate-700/50 bg-slate-100 dark:text-slate-300 text-slate-700'
          }`}
        >
          Tier {tier}
        </span>
        <span
          className={`text-[9px] font-mono px-1 rounded uppercase ${
            criticality === 'CRITICAL'
              ? 'text-red-400 font-bold'
              : criticality === 'HIGH'
              ? 'text-amber-400'
              : 'text-slate-400'
          }`}
        >
          {criticality}
        </span>
      </div>

      <div className="font-semibold text-xs truncate max-w-[150px] dark:text-white text-slate-900">
        {label}
      </div>

      <div className="mt-1.5 pt-1 border-t dark:border-slate-800 border-slate-200 flex items-center justify-between text-[10px] dark:text-slate-400 text-slate-500">
        <span>{owner}</span>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-indigo-400 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = {
  causalNode: CausalServiceNode,
};

// Collision-free layout coordinates for standard 12 microservices
const ARCHITECTURAL_COORDS = {
  'api-gateway': { x: 420, y: 30 },
  'auth-service': { x: 180, y: 170 },
  'user-service': { x: 180, y: 310 },
  'catalog-service': { x: 420, y: 170 },
  'cart-service': { x: 420, y: 310 },
  'order-service': { x: 680, y: 170 },
  'payment-service': { x: 680, y: 310 },
  'inventory-service': { x: 420, y: 450 },
  'notification-service': { x: 920, y: 310 },
  'recommendation-service': { x: 180, y: 450 },
  'postgres-primary': { x: 680, y: 470 },
  'message-queue': { x: 920, y: 470 },
  'cache-layer': { x: 420, y: 580 },
};

export default function CausalGraphView() {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [provenanceFilter, setProvenanceFilter] = useState('ALL'); // ALL, VALIDATED_CAUSAL, OBSERVED, DECLARED, UNCERTAIN
  const [minStrength, setMinStrength] = useState(0.0);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [edgeEvidence, setEdgeEvidence] = useState(null);
  const [loadingEvidence, setLoadingEvidence] = useState(false);

  // Experiment modal state
  const [isExperimentModalOpen, setIsExperimentModalOpen] = useState(false);
  const [targetService, setTargetService] = useState('payment-service');
  const [controlService, setControlService] = useState('auth-service');
  const [faultType, setFaultType] = useState('latency');
  const [faultIntensity, setFaultIntensity] = useState(0.85);
  const [faultDuration, setFaultDuration] = useState(25);
  const [runningExperiment, setRunningExperiment] = useState(false);
  const [experimentResult, setExperimentResult] = useState(null);
  const [experimentStep, setExperimentStep] = useState(0); // 0=idle, 1=baseline, 2=inject, 3=recovery, 4=done

  // Load Graph Data
  const loadGraph = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchCausalGraph();
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load causal graph:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Seed baseline calibrations if none exist
  const handleSeedBaselines = async () => {
    try {
      setLoading(true);
      await seedBaselineCalibrations();
      await loadGraph();
    } catch (err) {
      console.error('Failed to seed baselines:', err);
    } finally {
      setLoading(false);
    }
  };

  // Inspect edge evidence
  const handleEdgeClick = async (_, edge) => {
    if (!edge || !edge.data) return;
    const { source, target } = edge.data;
    setSelectedEdge(edge.data);
    setLoadingEvidence(true);
    try {
      const evidence = await fetchEdgeEvidence(source, target);
      setEdgeEvidence(evidence);
    } catch (err) {
      console.error('Failed to load edge evidence:', err);
      setEdgeEvidence(null);
    } finally {
      setLoadingEvidence(false);
    }
  };

  // Run Controlled Chaos Experiment
  const handleRunExperiment = async () => {
    setRunningExperiment(true);
    setExperimentResult(null);
    setExperimentStep(1); // Baseline capture

    try {
      await new Promise((r) => setTimeout(r, 600));
      setExperimentStep(2); // Chaos injection & observation

      const payload = {
        target_service: targetService,
        control_service: controlService,
        fault_type: faultType,
        intensity: parseFloat(faultIntensity),
        duration_seconds: parseInt(faultDuration, 10),
        environment: 'demo',
      };

      const result = await runCausalExperiment(payload);
      setExperimentStep(3); // Auto-restoration & recovery verification
      await new Promise((r) => setTimeout(r, 400));

      setExperimentResult(result);
      setExperimentStep(4); // Calibration updated
      await loadGraph();
    } catch (err) {
      console.error('Experiment failed:', err);
      alert(`Experiment error: ${err.response?.data?.detail || err.message}`);
      setExperimentStep(0);
    } finally {
      setRunningExperiment(false);
    }
  };

  // Build ReactFlow Nodes and Edges
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!graphData || !graphData.nodes) {
      return { flowNodes: [], flowEdges: [] };
    }

    const nodes = graphData.nodes.map((n, idx) => {
      const coord =
        ARCHITECTURAL_COORDS[n.id] || {
          x: (idx % 4) * 260 + 60,
          y: Math.floor(idx / 4) * 160 + 40,
        };

      return {
        id: n.id,
        type: 'causalNode',
        position: coord,
        data: {
          label: n.label,
          tier: n.tier,
          criticality: n.criticality,
          owner: n.owner,
          isTarget: runningExperiment && targetService === n.id,
          isControl: runningExperiment && controlService === n.id,
        },
      };
    });

    const edges = (graphData.edges || [])
      .filter((e) => {
        if (provenanceFilter !== 'ALL' && e.provenance !== provenanceFilter) return false;
        if (e.causal_strength < minStrength) return false;
        return true;
      })
      .map((e, idx) => {
        const isSelected =
          selectedEdge && selectedEdge.source === e.source && selectedEdge.target === e.target;

        // Color coding by provenance
        let strokeColor = '#64748b'; // DECLARED default
        let isAnimated = false;
        let strokeDasharray = undefined;

        if (e.provenance === 'VALIDATED_CAUSAL') {
          strokeColor = '#10b981'; // Vibrant emerald green
          isAnimated = true;
        } else if (e.provenance === 'OBSERVED') {
          strokeColor = '#f59e0b'; // Amber
          strokeDasharray = '5 5';
        } else if (e.provenance === 'UNCERTAIN') {
          strokeColor = '#f97316'; // Orange warning
          strokeDasharray = '3 3';
        }

        if (isSelected) {
          strokeColor = '#06b6d4'; // Cyan highlighted
        }

        // Width scaled by causal strength [1.5px to 5px]
        const strokeWidth = Math.max(1.8, Math.min(5.5, 1.5 + e.causal_strength * 3.8));

        return {
          id: `edge-${idx}-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          type: 'smoothstep',
          animated: isAnimated || isSelected,
          style: {
            stroke: strokeColor,
            strokeWidth: isSelected ? strokeWidth + 1.5 : strokeWidth,
            strokeDasharray,
            opacity: e.provenance === 'DECLARED' ? 0.45 : 0.95,
            cursor: 'pointer',
          },
          label: `${(e.causal_strength * 100).toFixed(0)}% • ${Math.round(e.propagation_delay_ms)}ms`,
          labelStyle: {
            fontSize: '10px',
            fill: isSelected ? '#38bdf8' : strokeColor,
            fontWeight: 700,
            fontFamily: 'monospace',
          },
          labelBgStyle: {
            fill: '#0f172a',
            fillOpacity: 0.85,
            stroke: strokeColor,
            strokeWidth: 1,
            rx: 4,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
            width: 14,
            height: 14,
          },
          data: e,
        };
      });

    return { flowNodes: nodes, flowEdges: edges };
  }, [graphData, provenanceFilter, minStrength, selectedEdge, runningExperiment, targetService, controlService]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const summary = graphData?.summary || {
    total_edges: 0,
    validated_causal_edges: 0,
    observed_edges: 0,
    declared_unvalidated_edges: 0,
    uncertain_edges: 0,
    mean_propagation_delay_ms: 0,
    mean_causal_confidence: 0,
    total_experiments_recorded: 0,
  };

  return (
    <div className="flex flex-col h-full gap-4 animate-in">
      {/* ================================================================
          TOP HEADER & SUMMARY KPIS
         ================================================================ */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-gradient-to-tr from-emerald-500/20 to-cyan-500/20 text-emerald-400 border border-emerald-500/30">
              <Network className="w-5 h-5 text-emerald-400" />
            </span>
            <div>
              <h1 className="text-xl font-bold dark:text-white text-slate-900">
                Chaos-Calibrated Causal Graph
              </h1>
              <p className="text-xs dark:text-slate-400 text-slate-500">
                Strengthens dependency architecture using evidence from controlled fault-injection experiments.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleSeedBaselines}
            title="Preload verified baselines"
            className="px-3 py-2 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700 flex items-center gap-1.5 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Seed Baselines
          </button>

          <button
            onClick={() => setIsExperimentModalOpen(true)}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-md shadow-emerald-500/20 flex items-center gap-2 transition-all"
          >
            <Flame className="w-4 h-4 text-amber-300" />
            Inject Calibration Fault
          </button>
        </div>
      </div>

      {/* Summary KPI Badges */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-xl bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Edges</span>
          <div className="text-lg font-black dark:text-white text-slate-900 mt-0.5">{summary.total_edges}</div>
          <span className="text-[10px] text-slate-500">Declared Topology</span>
        </div>

        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Validated Causal
          </span>
          <div className="text-lg font-black text-emerald-400 mt-0.5">{summary.validated_causal_edges}</div>
          <span className="text-[10px] text-emerald-500/80">≥3 runs • DiD &gt; 0.35</span>
        </div>

        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> Observed
          </span>
          <div className="text-lg font-black text-amber-400 mt-0.5">{summary.observed_edges}</div>
          <span className="text-[10px] text-amber-500/80">Pending repeat trials</span>
        </div>

        <div className="p-3 rounded-xl bg-slate-500/10 border border-slate-500/20">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Declared Only</span>
          <div className="text-lg font-black dark:text-slate-300 text-slate-700 mt-0.5">
            {summary.declared_unvalidated_edges}
          </div>
          <span className="text-[10px] text-slate-500">Awaiting chaos trial</span>
        </div>

        <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1">
            <Clock className="w-3 h-3" /> Mean Delay (τ)
          </span>
          <div className="text-lg font-black text-cyan-400 mt-0.5 font-mono">
            {summary.mean_propagation_delay_ms}ms
          </div>
          <span className="text-[10px] text-cyan-500/80">Propagation onset</span>
        </div>

        <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/30">
          <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1">
            <Shield className="w-3 h-3" /> Total Trials
          </span>
          <div className="text-lg font-black text-indigo-400 mt-0.5">{summary.total_experiments_recorded}</div>
          <span className="text-[10px] text-indigo-500/80">Audited in PostgreSQL</span>
        </div>
      </div>

      {/* ================================================================
          FILTER & PROVENANCE TOOLBAR
         ================================================================ */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-semibold text-slate-500 dark:text-slate-400">Provenance Filter:</span>
          {['ALL', 'VALIDATED_CAUSAL', 'OBSERVED', 'DECLARED', 'UNCERTAIN'].map((tier) => (
            <button
              key={tier}
              onClick={() => setProvenanceFilter(tier)}
              className={`px-2.5 py-1 rounded-lg font-bold transition-colors ${
                provenanceFilter === tier
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300'
              }`}
            >
              {tier === 'VALIDATED_CAUSAL'
                ? 'Validated (Green)'
                : tier === 'OBSERVED'
                ? 'Observed (Amber)'
                : tier === 'DECLARED'
                ? 'Declared (Slate)'
                : tier === 'UNCERTAIN'
                ? 'Uncertain (Orange)'
                : 'All Edges'}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-slate-500 dark:text-slate-400">Min Causal Strength:</span>
          <input
            type="range"
            min="0"
            max="0.9"
            step="0.05"
            value={minStrength}
            onChange={(e) => setMinStrength(parseFloat(e.target.value))}
            className="w-24 accent-emerald-500 cursor-pointer"
          />
          <span className="font-mono font-bold text-emerald-400 w-8">{(minStrength * 100).toFixed(0)}%</span>

          <button
            onClick={loadGraph}
            title="Refresh graph from DB"
            className="p-1.5 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ================================================================
          PRIMARY REACT FLOW CAUSAL GRAPH CANVAS
         ================================================================ */}
      <div className="flex-1 relative rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-950 min-h-[520px]">
        {loading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-sm text-cyan-400 font-semibold">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Computing Difference-in-Differences Causal Calibrations...
            </div>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onEdgeClick={handleEdgeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.3}
          maxZoom={1.5}
        >
          <Background color="#334155" gap={24} size={1} />
          <Controls className="!bg-slate-900 !border-slate-700 !text-white" />
          <MiniMap
            nodeColor="#6366f1"
            maskColor="rgba(15, 23, 42, 0.8)"
            className="!bg-slate-900 !border-slate-800 !rounded-xl"
          />
        </ReactFlow>

        {/* Floating Legend */}
        <div className="absolute bottom-4 left-4 p-3 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-xl text-[11px] space-y-1.5 pointer-events-none">
          <div className="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-1">
            Causal Provenance Legend
          </div>
          <div className="flex items-center gap-2 text-emerald-400">
            <span className="w-3 h-0.5 bg-emerald-400" />
            <span>Validated Causal (≥3 trials, DiD &gt; 0.35)</span>
          </div>
          <div className="flex items-center gap-2 text-amber-400">
            <span className="w-3 h-0.5 border-t border-dashed border-amber-400" />
            <span>Observed (1-2 trials, significant delta)</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <span className="w-3 h-0.5 bg-slate-500 opacity-60" />
            <span>Declared (Configured; unverified)</span>
          </div>
          <div className="flex items-center gap-2 text-orange-400">
            <span className="w-3 h-0.5 border-t border-dotted border-orange-400" />
            <span>Uncertain (Noisy / &lt;2.5σ baseline)</span>
          </div>
          <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
            Click any edge to inspect supporting experiments & DiD distribution.
          </div>
        </div>
      </div>

      {/* ================================================================
          EDGE EVIDENCE INSPECTOR MODAL / DRAWER
         ================================================================ */}
      {selectedEdge && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">
                  Causal Edge Evidence: {selectedEdge.source} → {selectedEdge.target}
                </h3>
              </div>
              <button
                onClick={() => setSelectedEdge(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingEvidence ? (
              <div className="p-8 text-center text-sm text-cyan-400">Loading empirical experiment data...</div>
            ) : edgeEvidence ? (
              <div className="space-y-4 text-xs">
                {/* Metric Summary Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80">
                    <span className="text-slate-400 text-[10px] uppercase font-bold">Causal Strength</span>
                    <div className="text-lg font-black text-emerald-400 font-mono mt-0.5">
                      {(edgeEvidence.calibration.causal_strength * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80">
                    <span className="text-slate-400 text-[10px] uppercase font-bold">Propagation Delay (τ)</span>
                    <div className="text-lg font-black text-cyan-400 font-mono mt-0.5">
                      {Math.round(edgeEvidence.calibration.propagation_delay_ms)} ms
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80">
                    <span className="text-slate-400 text-[10px] uppercase font-bold">Repeatability</span>
                    <div className="text-lg font-black text-indigo-400 font-mono mt-0.5">
                      {(edgeEvidence.calibration.repeatability * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80">
                    <span className="text-slate-400 text-[10px] uppercase font-bold">Experiments</span>
                    <div className="text-lg font-black text-amber-400 font-mono mt-0.5">
                      N = {edgeEvidence.calibration.experiment_count}
                    </div>
                  </div>
                </div>

                {/* Evidence Summary & Conclusion */}
                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                  <div className="font-bold text-slate-300">Empirical Synthesis</div>
                  <p className="text-slate-300 leading-relaxed">{edgeEvidence.causal_conclusion}</p>
                  <p className="text-cyan-400 font-semibold">{edgeEvidence.recommendation}</p>
                </div>

                {/* Supporting Experiments List */}
                <div>
                  <div className="font-bold text-slate-300 mb-2 flex items-center justify-between">
                    <span>Supporting Controlled Experiments ({edgeEvidence.supporting_experiments.length})</span>
                    <span className="text-[10px] text-slate-500 font-normal">Difference-in-Differences vs Control</span>
                  </div>

                  {edgeEvidence.supporting_experiments.length === 0 ? (
                    <div className="p-3 rounded-xl bg-slate-800/40 text-slate-400 text-center">
                      No controlled experiments have targeted {selectedEdge.target} yet. Run a calibration fault to collect evidence.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {edgeEvidence.supporting_experiments.map((exp, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 flex items-center justify-between"
                        >
                          <div>
                            <span className="font-mono text-cyan-300 font-bold">{exp.experiment_id}</span>
                            <div className="text-slate-400 text-[10px]">
                              {exp.fault_type.toUpperCase()} • Intensity {exp.intensity} • Control: {exp.control_service}
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-emerald-400 font-bold">{exp.status}</span>
                            <div className="text-slate-500 text-[10px]">
                              {exp.started_at ? new Date(exp.started_at).toLocaleTimeString() : 'Recent'}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setSelectedEdge(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold"
                  >
                    Close Inspector
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* ================================================================
          CONTROLLED CHAOS EXPERIMENT RUNNER MODAL
         ================================================================ */}
      {isExperimentModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 backdrop-blur-sm p-4 animate-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white">Inject Controlled Calibration Fault</h3>
              </div>
              {!runningExperiment && (
                <button
                  onClick={() => {
                    setIsExperimentModalOpen(false);
                    setExperimentResult(null);
                    setExperimentStep(0);
                  }}
                  className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Stepper Display during execution */}
            {runningExperiment && (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <div className="text-xs font-bold text-cyan-400 flex items-center gap-2">
                  <Activity className="w-4 h-4 animate-pulse" />
                  Controlled Chaos Experiment in Progress...
                </div>

                <div className="space-y-2 text-[11px]">
                  <div className={`flex items-center gap-2 ${experimentStep >= 1 ? 'text-emerald-400' : 'text-slate-500'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Step 1: Capture Pre-Injection Baseline (T0)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${experimentStep >= 2 ? 'text-emerald-400' : 'text-slate-500'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Step 2: Inject Bounded Fault on {targetService} ({faultType})</span>
                  </div>
                  <div className={`flex items-center gap-2 ${experimentStep >= 3 ? 'text-emerald-400' : 'text-slate-500'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Step 3: Measure Downstream Telemetry Delta & Propagation Delay (τ)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${experimentStep >= 4 ? 'text-emerald-400' : 'text-slate-500'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Step 4: Guaranteed Automated Restoration & Graph Calibration</span>
                  </div>
                </div>
              </div>
            )}

            {/* Execution Result Display */}
            {experimentResult && !runningExperiment && (
              <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/30 space-y-3 text-xs">
                <div className="flex items-center justify-between text-emerald-400 font-bold">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Experiment Completed & Fault Restored
                  </span>
                  <span className="font-mono text-[10px] text-slate-400">{experimentResult.experiment_id}</span>
                </div>

                <div className="space-y-1.5">
                  <div className="font-semibold text-slate-300">Observed Downstream Effects:</div>
                  {experimentResult.observed_impacts.map((imp, i) => (
                    <div
                      key={i}
                      className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center justify-between text-[11px]"
                    >
                      <div>
                        <span className="font-bold text-white">{imp.neighbor_service}</span>
                        <span className="text-slate-400 ml-1.5">({imp.direction})</span>
                      </div>
                      <div className="font-mono text-right">
                        <span className="text-amber-400">Δ {imp.delta_latency_ms}ms</span> •{' '}
                        <span className="text-cyan-400">τ = {imp.propagation_delay_ms}ms</span> •{' '}
                        <span className="text-emerald-400">DiD {imp.did_effect_size}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => {
                      setIsExperimentModalOpen(false);
                      setExperimentResult(null);
                    }}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
                  >
                    Done & View Calibrated Graph
                  </button>
                </div>
              </div>
            )}

            {/* Form Inputs (when idle) */}
            {!runningExperiment && !experimentResult && (
              <div className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1 font-semibold">Target Microservice (Fault Injection):</label>
                  <select
                    value={targetService}
                    onChange={(e) => setTargetService(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white font-semibold"
                  >
                    <option value="payment-service">payment-service (Port 9004)</option>
                    <option value="inventory-service">inventory-service (Port 9005)</option>
                    <option value="order-service">order-service (Port 9003)</option>
                    <option value="auth-service">auth-service (Port 9002)</option>
                    <option value="catalog-service">catalog-service (Port 9104)</option>
                    <option value="cart-service">cart-service (Port 9106)</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">Fault Type:</label>
                    <select
                      value={faultType}
                      onChange={(e) => setFaultType(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white font-semibold"
                    >
                      <option value="latency">Increased Latency (+1800ms)</option>
                      <option value="error">Elevated Errors (HTTP 500)</option>
                      <option value="unavailability">Unavailability (Blackhole)</option>
                      <option value="cpu_stress">CPU Saturation (95%)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">Control Comparison Service:</label>
                    <select
                      value={controlService}
                      onChange={(e) => setControlService(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white font-semibold"
                    >
                      <option value="auth-service">auth-service (Independent Control)</option>
                      <option value="search-service">search-service</option>
                      <option value="cache-layer">cache-layer</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">
                      Fault Intensity: {(faultIntensity * 100).toFixed(0)}%
                    </label>
                    <input
                      type="range"
                      min="0.2"
                      max="1.0"
                      step="0.05"
                      value={faultIntensity}
                      onChange={(e) => setFaultIntensity(e.target.value)}
                      className="w-full accent-amber-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-semibold">
                      Duration: {faultDuration} seconds
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="120"
                      step="5"
                      value={faultDuration}
                      onChange={(e) => setFaultDuration(e.target.value)}
                      className="w-full accent-cyan-500 cursor-pointer"
                    />
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                  <div className="font-bold text-amber-400 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5" /> Safety & Governance Constraints:
                  </div>
                  <div>• Bounded duration (≤300s) and intensity automatically enforced.</div>
                  <div>• Guaranteed rollback: fault is purged immediately upon experiment completion.</div>
                  <div>• Difference-in-Differences algorithm discounts global infrastructure confounders.</div>
                </div>

                <div className="flex justify-end gap-2.5 pt-2">
                  <button
                    onClick={() => setIsExperimentModalOpen(false)}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRunExperiment}
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold shadow-md shadow-emerald-500/20 flex items-center gap-2"
                  >
                    <Play className="w-3.5 h-3.5" /> Launch Controlled Experiment
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
