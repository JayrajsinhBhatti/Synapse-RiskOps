/**
 * frontend/src/pages/DashboardPage.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Unified SRE Command Center Dashboard.
 * Composes DependencyGraphView, RiskScorePanel, IncidentTimeline,
 * and GuidancePanel into an ultra-responsive operations console.
 */

import React, { useState } from 'react';
import DependencyGraphView from '../components/DependencyGraphView';
import RiskScorePanel from '../components/RiskScorePanel';
import IncidentTimeline from '../components/IncidentTimeline';
import GuidancePanel from '../components/GuidancePanel';
import { useIncidents, useServices } from '../hooks/useIncidents';
import {
  AlertCircle,
  Activity,
  Server,
  Timer,
  ShieldAlert,
} from 'lucide-react';

export default function DashboardPage({ activeView }) {
  const { data: incidentsData } = useIncidents();
  const { data: servicesData } = useServices();

  const [selectedIncident, setSelectedIncident] = useState(null);
  const [selectedServiceId, setSelectedServiceId] = useState(null);

  const incidents = Array.isArray(incidentsData) ? incidentsData : [];
  const services = Array.isArray(servicesData) ? servicesData : [];

  const activeIncidents = incidents.filter(
    (i) => i.status === 'OPEN' || i.status === 'INVESTIGATING'
  );
  const criticalCount = activeIncidents.filter((i) => i.severity === 'CRITICAL').length;

  const handleSelectIncident = (inc) => {
    setSelectedIncident(inc);
    if (inc?.service_id) {
      setSelectedServiceId(inc.service_id);
    }
  };

  const handleSelectService = (serviceId) => {
    setSelectedServiceId(serviceId);
    // Find if there is an active incident for this service
    const matchingIncident = activeIncidents.find((i) => i.service_id === serviceId);
    if (matchingIncident) {
      setSelectedIncident(matchingIncident);
    }
  };

  // View: Topology Full Screen
  if (activeView === 'topology') {
    return (
      <div className="h-[calc(100vh-120px)] flex flex-col gap-4">
        <DependencyGraphView
          selectedServiceId={selectedServiceId}
          activeIncidentServiceId={selectedIncident?.service_id}
          onSelectService={handleSelectService}
        />
      </div>
    );
  }

  // View: Incidents & Audit Full View
  if (activeView === 'incidents') {
    return (
      <div className="h-[calc(100vh-120px)] grid grid-cols-12 gap-6">
        <div className="col-span-6 h-full">
          <IncidentTimeline
            selectedIncidentId={selectedIncident?.id}
            onSelectIncident={handleSelectIncident}
          />
        </div>
        <div className="col-span-6 h-full">
          <GuidancePanel
            incident={selectedIncident || activeIncidents[0]}
            onClose={() => setSelectedIncident(null)}
          />
        </div>
      </div>
    );
  }

  // View: Risk Analytics
  if (activeView === 'risk') {
    return (
      <div className="h-[calc(100vh-120px)] flex flex-col gap-6">
        <div className="h-[480px]">
          <RiskScorePanel
            onSelectService={handleSelectService}
            selectedServiceId={selectedServiceId}
          />
        </div>
        <div className="flex-1 glass-card p-5">
          <h3 className="text-sm font-bold text-white mb-3">Service Health Diagnostics</h3>
          <div className="grid grid-cols-3 gap-3 overflow-y-auto max-h-[220px]">
            {services.map((svc) => (
              <div
                key={svc.id}
                onClick={() => handleSelectService(svc.id)}
                className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 cursor-pointer flex items-center justify-between"
              >
                <div>
                  <div className="font-semibold text-xs text-white">{svc.name}</div>
                  <div className="text-[10px] text-slate-400">Owner: {svc.owner || 'Core SRE'}</div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  Tier {svc.tier}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Default: Command Center Unified View
  return (
    <div className="space-y-6">
      {/* Top Telemetry KPIs Banner */}
      <div className="grid grid-cols-4 gap-4">
        {/* KPI 1: Active Incidents */}
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Active Incidents</div>
            <div className="text-2xl font-black text-white mt-1 flex items-baseline gap-2">
              <span>{activeIncidents.length}</span>
              {criticalCount > 0 && (
                <span className="text-xs font-semibold text-red-400 animate-pulse">
                  ({criticalCount} Critical)
                </span>
              )}
            </div>
          </div>
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${
            criticalCount > 0
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          }`}>
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>

        {/* KPI 2: Services Monitored */}
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Services Monitored</div>
            <div className="text-2xl font-black text-white mt-1">
              {services.length || 12}
            </div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
            <Server className="w-6 h-6" />
          </div>
        </div>

        {/* KPI 3: System Health Index */}
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">System Risk Index</div>
            <div className="text-2xl font-black text-emerald-400 mt-1">
              99.2%
            </div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        {/* KPI 4: Mean Time to Recovery */}
        <div className="glass-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400">Avg MTTR (Automated)</div>
            <div className="text-2xl font-black text-white mt-1">
              2m 14s
            </div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
            <Timer className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Grid: Left (Topology + Risk), Right (Incident Feed + Guidance) */}
      <div className="grid grid-cols-12 gap-6 items-start">
        {/* Left Column: 7 cols */}
        <div className="col-span-7 space-y-6">
          <div className="h-[480px]">
            <DependencyGraphView
              selectedServiceId={selectedServiceId}
              activeIncidentServiceId={selectedIncident?.service_id}
              onSelectService={handleSelectService}
            />
          </div>

          <div className="h-[400px]">
            <RiskScorePanel
              onSelectService={handleSelectService}
              selectedServiceId={selectedServiceId}
            />
          </div>
        </div>

        {/* Right Column: 5 cols */}
        <div className="col-span-5 space-y-6">
          <div className="h-[440px]">
            <IncidentTimeline
              selectedIncidentId={selectedIncident?.id}
              onSelectIncident={handleSelectIncident}
            />
          </div>

          <div className="h-[440px]">
            <GuidancePanel
              incident={selectedIncident || activeIncidents[0]}
              onClose={() => setSelectedIncident(null)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
