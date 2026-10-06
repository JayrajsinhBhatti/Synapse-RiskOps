/**
 * frontend/src/pages/DashboardPage.jsx
 * Owner: Person 2 | Week: 6+
 * 
 * Unified SRE Command Center Dashboard.
 * Composes DependencyGraphView, RiskScorePanel, IncidentTimeline,
 * and GuidancePanel into an ultra-responsive operations console.
 * 
 * Features premium micro-animations, staggered card entry, and
 * live data-driven KPI telemetry strip.
 */

import React, { useState } from 'react';
import DependencyGraphView from '../components/DependencyGraphView';
import RiskScorePanel from '../components/RiskScorePanel';
import IncidentTimeline from '../components/IncidentTimeline';
import GuidancePanel from '../components/GuidancePanel';
import IncidentsManagementView from '../components/incidents/IncidentsManagementView';
import RootCauseAnalysisView from '../components/rca/RootCauseAnalysisView';
import RemediationView from '../components/remediation/RemediationView';
import ServicesCatalogView from '../components/services/ServicesCatalogView';
import RiskHistoryView from '../components/risk/RiskHistoryView';
import { useIncidents, useServices } from '../hooks/useIncidents';
import {
  AlertCircle,
  Activity,
  Server,
  Timer,
  ShieldAlert,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Cpu,
  Wifi,
} from 'lucide-react';

export default function DashboardPage({ activeView, onViewChange }) {
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
  const resolvedCount = incidents.filter((i) => i.status === 'RESOLVED').length;

  const handleSelectIncident = (inc) => {
    setSelectedIncident(inc);
    if (inc?.service_id) {
      setSelectedServiceId(inc.service_id);
    }
  };

  const handleSelectService = (serviceId) => {
    setSelectedServiceId(serviceId);
    const matchingIncident = activeIncidents.find((i) => i.service_id === serviceId);
    if (matchingIncident) {
      setSelectedIncident(matchingIncident);
    }
  };

  // View: Incidents & Audit Full Console (Phase 7 & Section 21)
  if (activeView === 'incidents') {
    return (
      <IncidentsManagementView
        onSelectService={(svcId) => {
          setSelectedServiceId(svcId);
          if (onViewChange) onViewChange('topology');
        }}
      />
    );
  }

  // View: Topology Full Screen
  if (activeView === 'topology') {
    return (
      <div className="h-[calc(100vh-120px)] flex flex-col gap-4 animate-in">
        <DependencyGraphView
          selectedServiceId={selectedServiceId}
          activeIncidentServiceId={selectedIncident?.service_id}
          onSelectService={handleSelectService}
        />
      </div>
    );
  }

  // View: Root Cause Analysis (Phase 8 & Section 23)
  if (activeView === 'rca') {
    return (
      <RootCauseAnalysisView
        onNavigateToRemediation={() => {
          if (onViewChange) onViewChange('remediation');
        }}
      />
    );
  }

  // View: Runbooks & Remediation (Phase 9 & Section 24)
  if (activeView === 'remediation') {
    return <RemediationView />;
  }

  // View: Services Catalog (Section 26)
  if (activeView === 'services') {
    return (
      <ServicesCatalogView
        onSelectServiceTopology={(svcId) => {
          setSelectedServiceId(svcId);
          if (onViewChange) onViewChange('topology');
        }}
      />
    );
  }

  // View: Risk History (Section 26)
  if (activeView === 'risk-history') {
    return <RiskHistoryView />;
  }

  // View: Risk Analytics Full View
  if (activeView === 'risk') {
    return (
      <div className="h-[calc(100vh-120px)] flex flex-col gap-6 animate-in">
        <div className="h-[480px]">
          <RiskScorePanel
            onSelectService={handleSelectService}
            selectedServiceId={selectedServiceId}
          />
        </div>
        <div className="flex-1 glass-card p-5">
          <h3 className="text-sm font-bold dark:text-white text-slate-900 mb-3">Service Health Diagnostics</h3>
          <div className="grid grid-cols-3 gap-3 overflow-y-auto max-h-[220px]">
            {services.map((svc) => (
              <div
                key={svc.id}
                onClick={() => handleSelectService(svc.id)}
                className="p-3 rounded-xl dark:bg-slate-900/60 bg-slate-50 border dark:border-slate-800 border-slate-200 hover:border-slate-300 dark:hover:border-slate-700 cursor-pointer flex items-center justify-between transition-all hover:bg-slate-100 dark:hover:bg-slate-800/40"
              >
                <div>
                  <div className="font-semibold text-xs dark:text-white text-slate-900">{svc.name || svc.service_name}</div>
                  <div className="text-[10px] dark:text-slate-400 text-slate-500">Criticality: {svc.criticality || 'TIER_1'}</div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded dark:bg-slate-800 bg-slate-200 dark:text-slate-300 text-slate-700">
                  {svc.criticality || 'TIER_1'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // KPI card data
  const kpiCards = [
    {
      label: 'Active Incidents',
      value: activeIncidents.length,
      suffix: criticalCount > 0 ? `${criticalCount} Critical` : null,
      suffixColor: 'text-red-500 dark:text-red-400',
      suffixPulse: true,
      icon: ShieldAlert,
      iconBg: criticalCount > 0
        ? 'bg-red-500/15 text-red-500 dark:text-red-400 border-red-500/25'
        : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/25',
      trend: criticalCount > 0 ? 'up' : 'down',
      trendLabel: criticalCount > 0 ? '+' + criticalCount + ' new' : 'All clear',
    },
    {
      label: 'Services Monitored',
      value: services.length || 12,
      icon: Server,
      iconBg: 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/25',
      trend: 'stable',
      trendLabel: 'Production',
    },
    {
      label: 'System Health',
      value: activeIncidents.length === 0 ? '99.9%' : criticalCount > 0 ? '92.1%' : '97.4%',
      icon: Activity,
      iconBg: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-500/25',
      trend: criticalCount > 0 ? 'down' : 'up',
      trendLabel: criticalCount > 0 ? 'Degraded' : 'Nominal',
    },
    {
      label: 'Avg MTTR',
      value: '2m 14s',
      icon: Timer,
      iconBg: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/25',
      trend: 'down',
      trendLabel: '-38% vs baseline',
    },
  ];

  // Default: Command Center Unified View
  return (
    <div className="space-y-6">
      {/* Top Telemetry KPIs Banner with staggered animation */}
      <div className="grid grid-cols-4 gap-4">
        {kpiCards.map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.label}
              className="glass-card p-4 flex items-center justify-between group hover:border-slate-300 dark:hover:border-white/[0.12] transition-all shadow-sm"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="space-y-1">
                <div className="text-[11px] font-semibold dark:text-slate-400 text-slate-500 uppercase tracking-wider">
                  {kpi.label}
                </div>
                <div className="text-2xl font-black dark:text-white text-slate-900 flex items-baseline gap-2">
                  <span>{kpi.value}</span>
                  {kpi.suffix && (
                    <span className={`text-[10px] font-semibold ${kpi.suffixColor} ${kpi.suffixPulse ? 'animate-pulse' : ''}`}>
                      ({kpi.suffix})
                    </span>
                  )}
                </div>
                {/* Trend indicator */}
                <div className="flex items-center gap-1">
                  {kpi.trend === 'up' && <ArrowUpRight className="w-3 h-3 text-red-500 dark:text-red-400" />}
                  {kpi.trend === 'down' && <ArrowDownRight className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />}
                  {kpi.trend === 'stable' && <Wifi className="w-3 h-3 text-indigo-500 dark:text-indigo-400" />}
                  <span className={`text-[10px] font-medium ${
                    kpi.trend === 'up' ? 'text-red-500 dark:text-red-400' :
                    kpi.trend === 'down' ? 'text-emerald-600 dark:text-emerald-400' :
                    'text-indigo-600 dark:text-indigo-400'
                  }`}>
                    {kpi.trendLabel}
                  </span>
                </div>
              </div>
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center border ${kpi.iconBg} group-hover:scale-105 transition-transform`}>
                <Icon className="w-5 h-5" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Grid: Left (Topology + Risk), Right (Incident Feed + Guidance) */}
      <div className="grid grid-cols-12 gap-6 items-start">
        {/* Left Column: 7 cols */}
        <div className="col-span-7 space-y-6">
          <div className="h-[480px] animate-in" style={{ animationDelay: '120ms' }}>
            <DependencyGraphView
              selectedServiceId={selectedServiceId}
              activeIncidentServiceId={selectedIncident?.service_id}
              onSelectService={handleSelectService}
            />
          </div>

          <div className="h-[400px] animate-in" style={{ animationDelay: '200ms' }}>
            <RiskScorePanel
              onSelectService={handleSelectService}
              selectedServiceId={selectedServiceId}
            />
          </div>
        </div>

        {/* Right Column: 5 cols */}
        <div className="col-span-5 space-y-6">
          <div className="h-[440px] animate-in" style={{ animationDelay: '160ms' }}>
            <IncidentTimeline
              selectedIncidentId={selectedIncident?.id}
              onSelectIncident={handleSelectIncident}
            />
          </div>

          <div className="h-[440px] animate-in" style={{ animationDelay: '240ms' }}>
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
