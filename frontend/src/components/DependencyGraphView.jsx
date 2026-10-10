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

import { useTopology, useIncidents } from '../hooks/useIncidents';
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
          ? 'bg-red-950/90 border-red-500 shadow-red-500/40 ring-2 ring-red-400 animate-pulse text-white'
          : isHighlighted
          ? 'bg-amber-950/80 border-amber-500 shadow-amber-500/30 ring-1 ring-amber-400 text-white'
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
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${healthStyle.dot}`} />
          <span className="text-[10px] font-semibold uppercase dark:text-slate-400 text-slate-500">
            {health_status}
          </span>
        </div>
      </div>

      <div className={`font-semibold text-xs truncate max-w-[150px] ${isRootCause || isHighlighted ? 'text-white' : 'dark:text-white text-slate-900'}`}>
        {label}
      </div>

      <div className="mt-2 pt-1.5 border-t dark:border-slate-800 border-slate-200 flex items-center justify-between text-[10px]">
        <span className="dark:text-slate-400 text-slate-500">Risk Score</span>
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

/**
 * Computes collision-free, hierarchical layout coordinates for microservices.
 * 
 * Arranges services into logical architectural layers:
 * - Level 0: Ingress & API Gateways
 * - Level 1: Auth & Identity Services
 * - Level 2: Core Domain Microservices
 * - Level 3: Async & Secondary Microservices
 * - Level 4: Databases, Caches & Message Queues
 * 
 * Ensures minimum 250px horizontal pitch and 145px vertical pitch,
 * wrapping wider layers into staggered rows so NO services ever overlap.
 */
function getServiceArchitecturalLevel(service, inDegree, outDegree) {
  const name = (service.name || service.service_name || service.label || '').toLowerCase();
  const type = (service.service_type || '').toUpperCase();

  // Level 0: Ingress / Edge / Gateway
  if (type === 'GATEWAY' || name.includes('gateway') || name.includes('ingress') || name.includes('proxy') || name.includes('router')) {
    return 0;
  }

  // Level 4: Storage, Queue, Cache & Infrastructure Tier
  if (
    type === 'DATABASE' ||
    type === 'INFRASTRUCTURE' ||
    name.includes('postgres') ||
    name.includes('mysql') ||
    name.includes('database') ||
    name.includes('db-') ||
    name.includes('cache') ||
    name.includes('redis') ||
    name.includes('queue') ||
    name.includes('rabbitmq') ||
    name.includes('kafka')
  ) {
    return 4;
  }

  // Level 1: Identity & Authentication
  if (name.includes('auth') || name.includes('identity') || name.includes('token') || name.includes('login') || name.includes('user')) {
    return 1;
  }

  // Level 3: Async / Notifications / Search / Analytics
  if (
    name.includes('notification') ||
    name.includes('alert') ||
    name.includes('email') ||
    name.includes('search') ||
    name.includes('shipping') ||
    name.includes('audit') ||
    name.includes('analytics') ||
    name.includes('log') ||
    name.includes('monitor')
  ) {
    return 3;
  }

  // Level 2: Core Business Domain Microservices (orders, payments, inventory, etc.)
  return 2;
}

function computeDynamicTopologyCoordinates(services, dependencies) {
  if (!services || services.length === 0) return {};

  const inDegreeMap = {};
  const outDegreeMap = {};

  services.forEach((s) => {
    inDegreeMap[s.cleanId] = 0;
    outDegreeMap[s.cleanId] = 0;
  });

  dependencies.forEach((d) => {
    const src = d.source_service_id || d.source;
    const tgt = d.target_service_id || d.target;
    if (inDegreeMap[tgt] !== undefined) inDegreeMap[tgt] += 1;
    if (outDegreeMap[src] !== undefined) outDegreeMap[src] += 1;
  });

  const levelGroups = { 0: [], 1: [], 2: [], 3: [], 4: [] };
  services.forEach((s) => {
    const lvl = getServiceArchitecturalLevel(s, inDegreeMap[s.cleanId] || 0, outDegreeMap[s.cleanId] || 0);
    levelGroups[lvl].push(s);
  });

  const coordinates = {};
  const H_PITCH = 260; // 180px node + 80px horizontal gap
  const V_ROW_HEIGHT = 155; // 85px node + 70px vertical gap
  const MAX_PER_ROW = 4; // Wrap layers with more than 4 nodes into clean sub-rows

  // Determine canvas center width based on maximum row width
  let maxColsInDiagram = 1;
  [0, 1, 2, 3, 4].forEach((lvl) => {
    const count = levelGroups[lvl]?.length || 0;
    if (count > 0) {
      const cols = Math.min(count, MAX_PER_ROW);
      if (cols > maxColsInDiagram) maxColsInDiagram = cols;
    }
  });

  const canvasCenter = Math.max(520, (maxColsInDiagram * H_PITCH) / 2 + 60);
  let currentY = 40;

  [0, 1, 2, 3, 4].forEach((lvl) => {
    const svcs = levelGroups[lvl];
    if (!svcs || svcs.length === 0) return;

    // Break into sub-rows of MAX_PER_ROW
    const subRows = [];
    for (let i = 0; i < svcs.length; i += MAX_PER_ROW) {
      subRows.push(svcs.slice(i, i + MAX_PER_ROW));
    }

    subRows.forEach((rowSvcs) => {
      const rowCount = rowSvcs.length;
      const rowWidth = (rowCount - 1) * H_PITCH;
      const startX = Math.max(60, canvasCenter - rowWidth / 2);

      rowSvcs.forEach((svc, colIdx) => {
        const x = Math.round(startX + colIdx * H_PITCH);
        const y = Math.round(currentY);
        coordinates[svc.cleanId] = { x, y };
        if (svc.id !== undefined && svc.id !== null) {
          coordinates[String(svc.id)] = { x, y };
        }
        coordinates[svc.name] = { x, y };
      });

      currentY += V_ROW_HEIGHT;
    });

    currentY += 25; // Clean buffer between architectural layers
  });

  return coordinates;
}

export default function DependencyGraphView({
  selectedServiceId,
  activeIncidentServiceId,
  onSelectService,
}) {
  const { data: topologyData, isLoading, refetch } = useTopology();
  const { data: incidentsData } = useIncidents();
  const [selectedTier, setSelectedTier] = useState('ALL');

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!topologyData) {
      return { initialNodes: [], initialEdges: [] };
    }

    // Active incidents across the platform
    const rawIncidents = Array.isArray(incidentsData) ? incidentsData : [];
    const activeIncidents = rawIncidents.filter(
      (i) => i.status === 'OPEN' || i.status === 'INVESTIGATING' || i.status === 'ACKNOWLEDGED' || i.status === 'REMEDIATING'
    );

    // Set of active incident service identifiers
    const incidentServiceNames = new Set();
    const incidentServiceIds = new Set();
    const blastRadiusNames = new Set();

    if (activeIncidentServiceId) {
      incidentServiceIds.add(String(activeIncidentServiceId));
      incidentServiceNames.add(String(activeIncidentServiceId));
    }

    activeIncidents.forEach((inc) => {
      if (inc.service_id) incidentServiceIds.add(String(inc.service_id));
      if (inc.root_cause) incidentServiceNames.add(String(inc.root_cause));
      if (Array.isArray(inc.affected_services)) {
        inc.affected_services.forEach((aff) => blastRadiusNames.add(String(aff)));
      }
    });

    // Support both formats: backend ServiceTopologyResponse (services & dependencies) or nodes & edges
    const rawServices = topologyData.services || topologyData.nodes || [];
    const rawDependencies = topologyData.dependencies || topologyData.edges || [];

    // Map criticality to Tier with guaranteed cleanId
    const normalizedServices = rawServices.map((s, idx) => {
      const name = s.service_name || s.name || s.label || (s.id ? String(s.id) : `service-${idx + 1}`);
      const crit = (s.criticality || '').toUpperCase();
      const tier = s.tier || (crit === 'CRITICAL' ? 1 : crit === 'HIGH' ? 2 : 3);
      const cleanId = s.id !== undefined && s.id !== null ? String(s.id) : `svc-${name}-${idx}`;
      return {
        ...s,
        cleanId,
        name,
        tier,
      };
    });

    // Filter by tier
    const filteredServices = normalizedServices.filter((s) => {
      if (selectedTier === 'ALL') return true;
      return s.tier === Number(selectedTier);
    });

    // Build canonical ID resolver map
    const idResolver = {};
    filteredServices.forEach((s) => {
      idResolver[s.cleanId] = s.cleanId;
      if (s.id !== undefined && s.id !== null) idResolver[String(s.id)] = s.cleanId;
      if (s.name) idResolver[s.name] = s.cleanId;
      if (s.service_name) idResolver[s.service_name] = s.cleanId;
    });

    // Compute collision-free coordinates dynamically for this set of services
    const layoutCoordinates = computeDynamicTopologyCoordinates(filteredServices, rawDependencies);

    const nodes = filteredServices.map((svc, index) => {
      const coord =
        layoutCoordinates[svc.cleanId] ||
        (svc.id !== undefined && layoutCoordinates[String(svc.id)]) ||
        layoutCoordinates[svc.name] || {
          x: (index % 4) * 260 + 60,
          y: Math.floor(index / 4) * 155 + 40,
        };

      const normalizeSvc = (val) =>
        String(val || '')
          .toLowerCase()
          .replace(/[-_\s]+/g, '')
          .replace('service', '')
          .replace('svc', '');

      const svcNorm = normalizeSvc(svc.name);

      const matchingIncident = activeIncidents.find((inc) => {
        if (!inc) return false;
        if (
          String(inc.service_id) === svc.cleanId ||
          String(inc.service_id) === String(svc.id) ||
          String(inc.service_id) === svc.name
        ) {
          return true;
        }
        if (inc.root_cause) {
          if (inc.root_cause === svc.name || normalizeSvc(inc.root_cause) === svcNorm) {
            return true;
          }
        }
        if (inc.title && normalizeSvc(inc.title).includes(svcNorm)) {
          return true;
        }
        return false;
      });

      const isRootCause = Boolean(
        String(svc.cleanId) === String(activeIncidentServiceId) ||
        svc.name === String(activeIncidentServiceId) ||
        normalizeSvc(activeIncidentServiceId) === svcNorm ||
        incidentServiceIds.has(svc.cleanId) ||
        incidentServiceNames.has(svc.name) ||
        matchingIncident
      );

      const isInBlastRadiusList =
        blastRadiusNames.has(svc.name) ||
        blastRadiusNames.has(svc.cleanId) ||
        activeIncidents.some((inc) =>
          Array.isArray(inc.affected_services) &&
          inc.affected_services.some((aff) => normalizeSvc(aff) === svcNorm && aff !== inc.root_cause)
        );

      const isBlastRadius = !isRootCause && isInBlastRadiusList;

      const isHighlighted =
        String(svc.cleanId) === String(selectedServiceId) ||
        svc.name === String(selectedServiceId) ||
        isRootCause ||
        isBlastRadius;

      let calculatedRisk = isRootCause ? 0.965 : isBlastRadius ? 0.68 : 0.28;
      if (matchingIncident?.risk_score) {
        const rawScore = Number(matchingIncident.risk_score);
        calculatedRisk = rawScore > 1.0 ? rawScore / 100.0 : rawScore;
      }

      return {
        id: svc.cleanId,
        type: 'serviceNode',
        position: coord,
        data: {
          label: svc.name,
          tier: svc.tier,
          criticality: svc.criticality || 'HIGH',
          health_status: isRootCause ? 'critical' : isBlastRadius ? 'degraded' : 'healthy',
          risk_score: calculatedRisk,
          isRootCause,
          isHighlighted,
        },
      };
    });

    const edges = rawDependencies
      .filter((d) => {
        const rawSrc = d.source_service_id ?? d.source;
        const rawTgt = d.target_service_id ?? d.target;
        const resolvedSrc = idResolver[rawSrc] || idResolver[String(rawSrc)];
        const resolvedTgt = idResolver[rawTgt] || idResolver[String(rawTgt)];
        return Boolean(resolvedSrc && resolvedTgt && resolvedSrc !== resolvedTgt);
      })
      .map((d, idx) => {
        const rawSrc = d.source_service_id ?? d.source;
        const rawTgt = d.target_service_id ?? d.target;
        const src = idResolver[rawSrc] || idResolver[String(rawSrc)];
        const tgt = idResolver[rawTgt] || idResolver[String(rawTgt)];
        const srcName = d.source_service_name || src;
        const tgtName = d.target_service_name || tgt;

        const isIncidentEdge =
          incidentServiceIds.has(src) ||
          incidentServiceIds.has(tgt) ||
          incidentServiceNames.has(srcName) ||
          incidentServiceNames.has(tgtName) ||
          String(activeIncidentServiceId) === src ||
          String(activeIncidentServiceId) === tgt ||
          String(activeIncidentServiceId) === srcName ||
          String(activeIncidentServiceId) === tgtName;

        const isSelectedEdge =
          src === String(selectedServiceId) ||
          tgt === String(selectedServiceId) ||
          srcName === String(selectedServiceId) ||
          tgtName === String(selectedServiceId);

        const isImpacted = isIncidentEdge || isSelectedEdge;

        return {
          id: `edge-${idx}-${src}-${tgt}`,
          source: src,
          target: tgt,
          type: 'smoothstep',
          animated: isImpacted,
          style: {
            stroke: isIncidentEdge ? '#ef4444' : isSelectedEdge ? '#f59e0b' : '#6366f1',
            strokeWidth: isImpacted ? 2.5 : 1.5,
            opacity: isImpacted ? 0.95 : 0.45,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isIncidentEdge ? '#ef4444' : isSelectedEdge ? '#f59e0b' : '#6366f1',
            width: 15,
            height: 15,
          },
        };
      });

    return { initialNodes: nodes, initialEdges: edges };
  }, [topologyData, incidentsData, selectedTier, selectedServiceId, activeIncidentServiceId]);

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
      <div className="p-4 border-b dark:border-white/10 border-slate-200 flex items-center justify-between z-10 dark:bg-slate-900/40 bg-slate-50/90">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-indigo-600 dark:text-synapse-400" />
          <h2 className="text-base font-bold dark:text-white text-slate-900 tracking-wide">
            Microservice Topology & Blast Radius
          </h2>
        </div>

        {/* Tier Filter Tabs */}
        <div className="flex items-center gap-2">
          <div className="flex dark:bg-slate-800/80 bg-slate-100 p-0.5 rounded-lg border dark:border-slate-700/60 border-slate-200 text-xs">
            {['ALL', '1', '2', '3'].map((tier) => (
              <button
                key={tier}
                onClick={() => setSelectedTier(tier)}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  selectedTier === tier
                    ? 'bg-synapse-600 text-white shadow-sm'
                    : 'dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-950'
                }`}
              >
                {tier === 'ALL' ? 'All Tiers' : `Tier ${tier}`}
              </button>
            ))}
          </div>

          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg dark:bg-slate-800 bg-white dark:hover:bg-slate-700 hover:bg-slate-100 dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-950 border dark:border-transparent border-slate-200 shadow-sm transition-colors"
            title="Refresh Topology"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ReactFlow Canvas */}
      <div className="flex-1 w-full h-[520px] dark:bg-slate-950/70 bg-slate-50/60 relative">
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
            <Background color="#94a3b8" gap={20} size={1} />
            <Controls className="!bg-white dark:!bg-slate-900 !border-slate-300 dark:!border-slate-700 !text-slate-700 dark:!text-slate-200 fill-slate-700 dark:fill-slate-200" />
            <MiniMap
              nodeColor={(node) => {
                if (node.data.isRootCause) return '#ef4444';
                if (node.data.tier === 1) return '#6366f1';
                if (node.data.tier === 2) return '#06b6d4';
                return '#64748b';
              }}
              maskColor="rgba(15, 23, 42, 0.7)"
              className="!bg-white dark:!bg-slate-900 !border-slate-200 dark:!border-slate-800 rounded-lg overflow-hidden shadow-sm"
            />
          </ReactFlow>
        )}
      </div>

      {/* Legend Footer */}
      <div className="px-4 py-2 dark:bg-slate-900/60 bg-slate-50 border-t dark:border-white/5 border-slate-200 flex items-center justify-between text-[11px] dark:text-slate-400 text-slate-600">
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
          <span className="flex items-center gap-1 text-red-500 dark:text-red-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" /> Active Root Cause
          </span>
          <span className="text-slate-400">|</span>
          <span>Click any node to inspect blast radius</span>
        </div>
      </div>
    </div>
  );
}
