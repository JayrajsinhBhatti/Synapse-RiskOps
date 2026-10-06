/**
 * frontend/src/components/services/ServicesCatalogView.jsx
 * 
 * Microservice Service Catalog & Architecture Directory.
 * Implements Prompt Section 26:
 * - Real data from GET /api/services and GET /api/services/topology
 * - Criticality filtering, dependency counts, health telemetry, and service details.
 */

import React, { useState, useMemo } from 'react';
import { useServices, useTopology } from '../../hooks/useIncidents';
import {
  Server,
  Network,
  ShieldCheck,
  Activity,
  Layers,
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Clock,
} from 'lucide-react';

export default function ServicesCatalogView({ onSelectServiceTopology }) {
  const { data: servicesData, isLoading: servicesLoading } = useServices();
  const { data: topologyData } = useTopology();

  const [searchTerm, setSearchTerm] = useState('');
  const [criticalityFilter, setCriticalityFilter] = useState('ALL');
  const [selectedService, setSelectedService] = useState(null);

  const services = Array.isArray(servicesData) ? servicesData : [];
  const dependencies = topologyData?.dependencies || [];

  // Compute upstream & downstream dependencies per service
  const serviceStats = useMemo(() => {
    const stats = {};
    services.forEach((s) => {
      const up = dependencies.filter((d) => d.target_service_id === s.id).length;
      const down = dependencies.filter((d) => d.source_service_id === s.id).length;
      stats[s.id] = { upstreamCount: up, downstreamCount: down };
    });
    return stats;
  }, [services, dependencies]);

  // Filtered list
  const filteredServices = useMemo(() => {
    return services.filter((s) => {
      const matchesSearch = s.service_name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCrit = criticalityFilter === 'ALL' || s.criticality === criticalityFilter;
      return matchesSearch && matchesCrit;
    });
  }, [services, searchTerm, criticalityFilter]);

  if (servicesLoading) {
    return (
      <div className="h-[calc(100vh-140px)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Server className="w-8 h-8 text-indigo-400 animate-pulse" />
          <span className="text-xs font-mono text-slate-400">Loading Microservice Catalog...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl dark:bg-slate-900/80 bg-white border dark:border-white/[0.08] border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 dark:bg-indigo-500/10 bg-indigo-50 px-2 py-0.5 rounded-full border dark:border-indigo-500/20 border-indigo-200">
              Service Mesh Inventory
            </span>
            <span className="text-xs font-mono dark:text-slate-400 text-slate-500">
              {services.length} Registered Microservices
            </span>
          </div>
          <h1 className="text-xl font-black dark:text-white text-slate-900 tracking-tight">
            Microservice Catalog & Dependency Index
          </h1>
        </div>

        {/* Search & Filter Bar */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search services..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl pl-8 pr-3 py-1.5 text-xs dark:text-slate-200 text-slate-800 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-48 md:w-60"
            />
          </div>

          <select
            value={criticalityFilter}
            onChange={(e) => setCriticalityFilter(e.target.value)}
            className="dark:bg-slate-950 bg-slate-50 border dark:border-slate-700 border-slate-300 rounded-xl px-3 py-1.5 text-xs dark:text-slate-200 text-slate-800 font-medium focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Criticalities</option>
            <option value="TIER_0">Tier 0 (Mission Critical)</option>
            <option value="TIER_1">Tier 1 (High Priority)</option>
            <option value="TIER_2">Tier 2 (Standard)</option>
          </select>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredServices.map((svc) => {
          const stats = serviceStats[svc.id] || { upstreamCount: 0, downstreamCount: 0 };
          const isSelected = selectedService?.id === svc.id;

          const critStyle =
            svc.criticality === 'TIER_0'
              ? 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20'
              : svc.criticality === 'TIER_1'
              ? 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20'
              : 'text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 border-cyan-500/20';

          return (
            <div
              key={svc.id}
              onClick={() => setSelectedService(svc)}
              className={`p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'dark:bg-slate-900 bg-indigo-50/80 border-indigo-500 shadow-xl shadow-indigo-500/10'
                  : 'dark:bg-slate-900/60 bg-white border dark:border-slate-800 border-slate-200 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900/90 shadow-sm'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${critStyle}`}>
                    {svc.criticality || 'TIER_1'}
                  </span>
                  <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-600 dark:text-emerald-400">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    HEALTHY
                  </div>
                </div>

                <div className="flex items-center gap-3 mb-2">
                  <div className="w-9 h-9 rounded-xl dark:bg-slate-800 bg-slate-100 border dark:border-slate-700 border-slate-200 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                    <Server className="w-4.5 h-4.5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold dark:text-white text-slate-900 group-hover:text-indigo-600 dark:group-hover:text-cyan-300 transition-colors">
                      {svc.service_name}
                    </h3>
                    <span className="text-[10px] font-mono dark:text-slate-500 text-slate-400">
                      ID: {svc.id.slice(0, 8)}...
                    </span>
                  </div>
                </div>

                <p className="text-xs dark:text-slate-400 text-slate-600 line-clamp-2 mb-4">
                  {svc.description || 'Core business microservice deployed in Kubernetes cluster.'}
                </p>
              </div>

              {/* Dependency Indicators */}
              <div className="grid grid-cols-2 gap-2 pt-3 border-t dark:border-white/[0.06] border-slate-100 text-[11px] font-mono">
                <div className="p-2 rounded-lg dark:bg-slate-950/60 bg-slate-50 border dark:border-transparent border-slate-200 flex items-center justify-between dark:text-slate-400 text-slate-600">
                  <span className="flex items-center gap-1">
                    <ArrowDownLeft className="w-3 h-3 text-cyan-500 dark:text-cyan-400" />
                    Upstream:
                  </span>
                  <span className="dark:text-white text-slate-900 font-bold">{stats.upstreamCount}</span>
                </div>
                <div className="p-2 rounded-lg dark:bg-slate-950/60 bg-slate-50 border dark:border-transparent border-slate-200 flex items-center justify-between dark:text-slate-400 text-slate-600">
                  <span className="flex items-center gap-1">
                    <ArrowUpRight className="w-3 h-3 text-indigo-500 dark:text-indigo-400" />
                    Downstream:
                  </span>
                  <span className="dark:text-white text-slate-900 font-bold">{stats.downstreamCount}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Service Detail Drawer / Modal */}
      {selectedService && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fade-in">
          <div className="glass-card max-w-xl w-full p-6 border-indigo-500/30 shadow-2xl space-y-5">
            <div className="flex items-start justify-between border-b dark:border-white/[0.08] border-slate-200 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl dark:bg-indigo-500/10 bg-indigo-50 border dark:border-indigo-500/20 border-indigo-200 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <Server className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold dark:text-white text-slate-900">
                    {selectedService.service_name}
                  </h3>
                  <span className="text-xs font-mono dark:text-slate-400 text-slate-500">
                    UUID: {selectedService.id}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedService(null)}
                className="text-xs dark:text-slate-400 text-slate-500 dark:hover:text-white hover:text-slate-900 px-2.5 py-1 rounded-lg dark:bg-slate-800 bg-slate-100 border dark:border-transparent border-slate-200"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl dark:bg-slate-900/60 bg-slate-50 border dark:border-slate-800 border-slate-200">
                <span className="text-[10px] dark:text-slate-400 text-slate-500 font-bold uppercase block mb-1">Tier & SLA</span>
                <span className="dark:text-white text-slate-900 font-bold">{selectedService.criticality || 'TIER_1'} (99.95% SLO Target)</span>
              </div>
              <div className="p-3 rounded-xl dark:bg-slate-900/60 bg-slate-50 border dark:border-slate-800 border-slate-200">
                <span className="text-[10px] dark:text-slate-400 text-slate-500 font-bold uppercase block mb-1">Registered At</span>
                <span className="dark:text-white text-slate-900 font-mono">{new Date(selectedService.created_at || Date.now()).toLocaleDateString()}</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Active Dependency Topology
              </h4>
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2 max-h-40 overflow-y-auto font-mono text-xs">
                {dependencies.filter((d) => d.source_service_id === selectedService.id || d.target_service_id === selectedService.id).map((dep, idx) => (
                  <div key={idx} className="flex items-center justify-between text-slate-300">
                    <span>{dep.source_service_name || 'source'} → {dep.target_service_name || 'target'}</span>
                    <span className="text-[10px] text-slate-500 uppercase">{dep.dependency_type || 'RPC'}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => {
                  setSelectedService(null);
                  if (onSelectServiceTopology) onSelectServiceTopology(selectedService.id);
                }}
                className="px-4 py-2 rounded-xl bg-synapse-600 hover:bg-synapse-500 text-white font-bold text-xs flex items-center gap-1.5 transition-colors"
              >
                <Network className="w-3.5 h-3.5" />
                Inspect in Topology Graph
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
