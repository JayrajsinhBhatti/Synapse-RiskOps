/**
 * frontend/src/components/DependencyGraphView.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Visualizes the 12 microservices and 19 dependencies using React Flow.
 * Highlights downstream blast radius and propagation path for active incidents.
 */

import React, { useMemo, useState, useEffect } from 'react';
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

import { useTopology } from '../hooks/useIncidents';
import { getRiskScoreStyle, getServiceHealthBadge } from '../utils/formatters';
import { Network, Server, Layers, AlertCircle, RefreshCw } from 'lucide-react';

/**
 * Custom Node component representing a Microservice
 */
function ServiceNode({ data }) {
  const { label, tier, health_status, risk_score, isHighlighted, isRootCause, criticality } = data;
  const riskStyle = getRiskScoreStyle(risk_score);
  const healthStyle = getServiceHealthBadge(health_status);

  return (
    <div
      className={`px-3 py-2.5 rounded-xl border transition-all duration-300 min-w-[170px] shadow-lg backdrop-blur-md ${
        isRootCause
          ? 'bg-red-950/90 border-red-500 shadow-red-500/40 ring-2 ring-red-400 animate-pulse'
          : isHighlighted
          ? 'bg-amber-950/80 border-amber-500 shadow-amber-500/30 ring-1 ring-amber-400'
          : 'bg-slate-900/90 border-slate-700/80 hover:border-slate-500'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-indigo-400 !w-2 !h-2" />

      <div className="flex items-center justify-between mb-1.5">
        <span
          className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
            tier === 1
              ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-500/40'
              : tier === 2
              ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/40'
              : 'bg-slate-700/50 text-slate-300'
          }`}
        >
          Tier {tier}
        </span>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${healthStyle.dot}`} />
          <span className="text-[10px] font-semibold uppercase text-slate-400">
            {health_status}
          </span>
        </div>
      </div>

      <div className="font-semibold text-xs text-white truncate max-w-[150px]">
        {label}
      </div>

      <div className="mt-2 pt-1.5 border-t border-slate-800 flex items-center justify-between text-[10px]">
        <span className="text-slate-400">Risk Score</span>
        <span className="font-mono font-bold" style={{ color: riskStyle.color }}>
          {(Number(risk_score) || 0).toFixed(2)}
        </span>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-indigo-400 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = {
  serviceNode: ServiceNode,
};

// Fixed positions arranged logically by Tier for clean architecture rendering
const LAYOUT_COORDINATES = {
  'api-gateway': { x: 380, y: 30 },
  'auth-service': { x: 140, y: 140 },
  'order-service': { x: 380, y: 140 },
  'payment-gateway': { x: 620, y: 140 },
  'payment-service': { x: 620, y: 140 },
  'inventory-service': { x: 260, y: 260 },
  'shipping-service': { x: 500, y: 260 },
  'notification-service': { x: 740, y: 260 },
  'recommendation-engine': { x: 20, y: 260 },
  'analytics-pipeline': { x: 140, y: 380 },
  'audit-service': { x: 380, y: 380 },
  'cache-layer': { x: 620, y: 380 },
  'log-aggregator': { x: 620, y: 380 },
  'monitoring-agent': { x: 380, y: 490 },
};

export default function DependencyGraphView({
  selectedServiceId,
  activeIncidentServiceId,
  onSelectService,
}) {
  const { data: topologyData, isLoading, refetch } = useTopology();
  const [selectedTier, setSelectedTier] = useState('ALL');

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!topologyData) {
      return { initialNodes: [], initialEdges: [] };
    }

    // Support both formats: backend ServiceTopologyResponse (services & dependencies) or nodes & edges
    const rawServices = topologyData.services || topologyData.nodes || [];
    const rawDependencies = topologyData.dependencies || topologyData.edges || [];

    // Map criticality to Tier
    const normalizedServices = rawServices.map((s) => {
      const name = s.service_name || s.name || s.label || s.id;
      const crit = (s.criticality || '').toUpperCase();
      const tier = s.tier || (crit === 'CRITICAL' ? 1 : crit === 'HIGH' ? 2 : 3);
      return {
        ...s,
        cleanId: s.id,
        name,
        tier,
      };
    });

    // Filter by tier
    const filteredServices = normalizedServices.filter((s) => {
      if (selectedTier === 'ALL') return true;
      return s.tier === Number(selectedTier);
    });

    const activeServiceIds = new Set(filteredServices.map((s) => s.cleanId));
    const activeServiceNames = new Set(filteredServices.map((s) => s.name));

    const nodes = filteredServices.map((svc, index) => {
      const coord =
        LAYOUT_COORDINATES[svc.name] || {
          x: (index % 4) * 220 + 80,
          y: Math.floor(index / 4) * 140 + 40,
        };

      const isRootCause =
        svc.cleanId === activeIncidentServiceId || svc.name === activeIncidentServiceId;
      const isHighlighted =
        svc.cleanId === selectedServiceId || svc.name === selectedServiceId;

      return {
        id: svc.cleanId,
        type: 'serviceNode',
        position: coord,
        data: {
          label: svc.name,
          tier: svc.tier,
          criticality: svc.criticality || 'HIGH',
          health_status: isRootCause ? 'critical' : 'healthy',
          risk_score: isRootCause ? 0.94 : 0.28,
          isRootCause,
          isHighlighted,
        },
      };
    });

    const edges = rawDependencies
      .filter((d) => {
        const src = d.source_service_id || d.source;
        const tgt = d.target_service_id || d.target;
        return activeServiceIds.has(src) && activeServiceIds.has(tgt);
      })
      .map((d, idx) => {
        const src = d.source_service_id || d.source;
        const tgt = d.target_service_id || d.target;
        const srcName = d.source_service_name || src;
        const tgtName = d.target_service_name || tgt;

        const isImpacted =
          src === activeIncidentServiceId ||
          tgt === activeIncidentServiceId ||
          srcName === activeIncidentServiceId ||
          tgtName === activeIncidentServiceId ||
          src === selectedServiceId ||
          srcName === selectedServiceId;

        return {
          id: `edge-${idx}-${src}-${tgt}`,
          source: src,
          target: tgt,
          type: 'smoothstep',
          animated: isImpacted,
          style: {
            stroke: isImpacted ? '#ef4444' : '#6366f1',
            strokeWidth: isImpacted ? 2.5 : 1.5,
            opacity: isImpacted ? 0.95 : 0.45,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isImpacted ? '#ef4444' : '#6366f1',
            width: 15,
            height: 15,
          },
        };
      });

    return { initialNodes: nodes, initialEdges: edges };
  }, [topologyData, selectedTier, selectedServiceId, activeIncidentServiceId]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = (_, node) => {
    if (onSelectService) {
      onSelectService(node.id);
    }
  };

  return (
    <div className="glass-card flex flex-col h-full overflow-hidden relative">
      {/* Top Toolbar */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between z-10 bg-slate-900/40">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-synapse-400" />
          <h2 className="text-base font-bold text-white tracking-wide">
            Microservice Topology & Blast Radius
          </h2>
        </div>

        {/* Tier Filter Tabs */}
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700/60 text-xs">
            {['ALL', '1', '2', '3'].map((tier) => (
              <button
                key={tier}
                onClick={() => setSelectedTier(tier)}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  selectedTier === tier
                    ? 'bg-synapse-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tier === 'ALL' ? 'All Tiers' : `Tier ${tier}`}
              </button>
            ))}
          </div>

          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Refresh Topology"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ReactFlow Canvas */}
      <div className="flex-1 w-full h-[520px] bg-slate-950/70 relative">
        {isLoading ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm">
            Loading service topology...
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#334155" gap={20} size={1} />
            <Controls className="!bg-slate-900 !border-slate-700 !text-slate-200 fill-slate-200" />
            <MiniMap
              nodeColor={(node) => {
                if (node.data.isRootCause) return '#ef4444';
                if (node.data.tier === 1) return '#6366f1';
                if (node.data.tier === 2) return '#06b6d4';
                return '#64748b';
              }}
              maskColor="rgba(15, 23, 42, 0.7)"
              className="!bg-slate-900 !border-slate-800 rounded-lg overflow-hidden"
            />
          </ReactFlow>
        )}
      </div>

      {/* Legend Footer */}
      <div className="px-4 py-2 bg-slate-900/60 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-indigo-500" /> Tier 1 Core
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-cyan-500" /> Tier 2 Business
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-slate-500" /> Tier 3 Support
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-red-400">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" /> Active Root Cause
          </span>
          <span className="text-slate-500">|</span>
          <span>Click any node to inspect blast radius</span>
        </div>
      </div>
    </div>
  );
}
