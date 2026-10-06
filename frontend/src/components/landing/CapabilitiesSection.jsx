/**
 * frontend/src/components/landing/CapabilitiesSection.jsx
 * 
 * 8 Core capabilities cards representing the full platform power.
 */

import React from 'react';
import {
  Activity,
  TrendingDown,
  GitBranch,
  ShieldAlert,
  Network,
  Terminal,
  Radio,
  UserCheck,
} from 'lucide-react';

export function CapabilitiesSection() {
  const capabilities = [
    {
      icon: Activity,
      title: 'Anomaly Detection',
      desc: 'Multivariate statistical & Isolation Forest models identifying telemetry divergence across CPU, latency, and error rates.',
      badge: 'ML Engine',
    },
    {
      icon: TrendingDown,
      title: 'Failure Prediction',
      desc: 'Predictive degradation forecasting giving SRE teams early lead time before customer SLA impact occurs.',
      badge: 'Proactive Lead Time',
    },
    {
      icon: GitBranch,
      title: 'Root Cause Analysis',
      desc: 'Topological graph reasoning eliminating alert storms by tracing symptoms directly to the originating service.',
      badge: 'Graph Engine',
    },
    {
      icon: ShieldAlert,
      title: 'Risk Intelligence',
      desc: 'Tiered health scoring (Healthy < 0.40, Watch 0.40–0.70, Critical ≥ 0.70) calibrated across 12 microservices.',
      badge: 'Composite Scoring',
    },
    {
      icon: Network,
      title: 'Service Topology',
      desc: 'Live architecture dependency map visualizing 19 critical pathways with dynamic blast radius highlighting.',
      badge: 'React Flow Canvas',
    },
    {
      icon: Terminal,
      title: 'Runbook Automation',
      desc: 'Curated library of tested mitigation playbooks for pod rescaling, cache flushes, and connection pool resets.',
      badge: 'Ansible Runners',
    },
    {
      icon: Radio,
      title: 'Real-Time Incident Stream',
      desc: 'Instant SSE broadcasts delivering state transitions directly to active operations screens with zero polling.',
      badge: 'SSE Pub/Sub',
    },
    {
      icon: UserCheck,
      title: 'Human Escalation',
      desc: 'Confidence-routed approval gates ensuring high-risk remediations require explicit SRE / Lead sign-off.',
      badge: 'RBAC Governed',
    },
  ];

  return (
    <section id="capabilities" className="py-24 bg-slate-950/60 border-t border-white/5 relative">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs uppercase font-mono font-bold text-cyan-400 tracking-wider">
            Enterprise Capabilities
          </span>
          <h2 className="text-3xl font-extrabold text-white mt-2 tracking-tight">
            Built for High-Stakes Operations
          </h2>
          <p className="text-sm text-slate-400 mt-3 leading-relaxed">
            Every layer of the platform is designed to shorten MTTR and eliminate manual incident toil.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {capabilities.map((cap, i) => {
            const Icon = cap.icon;
            return (
              <div
                key={i}
                className="saas-card p-5 flex flex-col justify-between hover:border-slate-600 transition-all group"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-cyan-400 group-hover:scale-105 group-hover:border-cyan-500/40 transition-all">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      {cap.badge}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-white mb-2">{cap.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{cap.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default CapabilitiesSection;
