/**
 * frontend/src/components/landing/ArchitectureSection.jsx
 * 
 * Interactive Architectural Pipeline Visualizer:
 * Telemetry -> ML Engine -> Risk Engine -> Root Cause Analysis -> Confidence Router -> Remediation / Escalation.
 */

import React from 'react';
import {
  Activity,
  Cpu,
  ShieldCheck,
  GitBranch,
  Sliders,
  Terminal,
  UserCheck,
  ArrowRight,
  ArrowDown,
} from 'lucide-react';

export function ArchitectureSection() {
  const pipelineNodes = [
    {
      title: 'Telemetry Ingest',
      subtitle: 'Metrics, Spans, Logs',
      tech: 'OpenTelemetry • Prometheus',
      icon: Activity,
      color: 'border-blue-500/40 text-blue-400',
    },
    {
      title: 'ML Anomaly Engine',
      subtitle: 'Z-Score & Isolation Forest',
      tech: 'Scikit-learn • Python 3.11',
      icon: Cpu,
      color: 'border-indigo-500/40 text-indigo-400',
    },
    {
      title: 'Risk Scoring Engine',
      subtitle: 'Multi-factor Severity Index',
      tech: 'RiskScorer • Tier Analysis',
      icon: ShieldCheck,
      color: 'border-cyan-500/40 text-cyan-400',
    },
    {
      title: 'Root Cause (RCA)',
      subtitle: 'Graph Traversal & Causal Chains',
      tech: 'NetworkX • Topology Engine',
      icon: GitBranch,
      color: 'border-amber-500/40 text-amber-400',
    },
    {
      title: 'Confidence Router',
      subtitle: 'Threshold Decision Engine',
      tech: 'Tiers: Autonomous vs Supervised',
      icon: Sliders,
      color: 'border-purple-500/40 text-purple-400',
    },
  ];

  return (
    <section id="architecture" className="py-24 relative overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs uppercase font-mono font-bold text-cyan-400 tracking-wider">
            System Architecture
          </span>
          <h2 className="text-3xl font-extrabold text-white mt-2 tracking-tight">
            Intelligent Pipeline Architecture
          </h2>
          <p className="text-sm text-slate-400 mt-3 leading-relaxed">
            How Synapse RiskOps connects real-time distributed telemetry to automated self-healing playbooks.
          </p>
        </div>

        {/* Pipeline Visual Flow */}
        <div className="saas-card p-8 relative overflow-hidden">
          {/* Horizontal Desktop Flow */}
          <div className="hidden lg:grid grid-cols-5 gap-3 relative z-10">
            {pipelineNodes.map((node, i) => {
              const Icon = node.icon;
              return (
                <div key={i} className="relative flex flex-col items-center text-center">
                  <div className={`w-full p-4 rounded-xl bg-slate-900/90 border ${node.color} shadow-lg transition-transform hover:-translate-y-1`}>
                    <div className="w-10 h-10 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto mb-3">
                      <Icon className="w-5 h-5" />
                    </div>
                    <h4 className="text-xs font-bold text-white mb-1">{node.title}</h4>
                    <p className="text-[11px] text-slate-300 leading-tight mb-2">{node.subtitle}</p>
                    <span className="text-[9px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      {node.tech}
                    </span>
                  </div>

                  {i < pipelineNodes.length - 1 && (
                    <div className="hidden lg:flex absolute top-1/2 -right-3 -translate-y-1/2 z-20 w-6 h-6 rounded-full bg-slate-950 border border-slate-700 items-center justify-center text-slate-400 shadow-sm">
                      <ArrowRight className="w-3 h-3" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Mobile Vertical Flow */}
          <div className="lg:hidden flex flex-col gap-4">
            {pipelineNodes.map((node, i) => {
              const Icon = node.icon;
              return (
                <div key={i} className="flex flex-col items-center">
                  <div className={`w-full p-4 rounded-xl bg-slate-900/90 border ${node.color} flex items-center gap-4`}>
                    <div className="w-10 h-10 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white">{node.title}</h4>
                      <p className="text-[11px] text-slate-300">{node.subtitle}</p>
                      <span className="text-[9px] font-mono text-slate-400 mt-1 inline-block">
                        {node.tech}
                      </span>
                    </div>
                  </div>
                  {i < pipelineNodes.length - 1 && (
                    <ArrowDown className="w-4 h-4 text-slate-600 my-1" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Dual Branching Outcomes (Automated vs Supervised) */}
          <div className="mt-8 pt-8 border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <Terminal className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-mono font-bold uppercase text-emerald-400 tracking-wider">
                  Path A: Autonomous Execution (&ge; 85% Confidence)
                </span>
                <h5 className="text-xs font-bold text-white mt-0.5">Automated Runbook Mitigation</h5>
                <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                  Ansible Semaphore & Docker/K8s orchestrators immediately trigger tested playbooks, scaling replicas or clearing pools with zero manual delay.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
                <UserCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-mono font-bold uppercase text-amber-400 tracking-wider">
                  Path B: Supervised SRE Review (&lt; 85% Confidence)
                </span>
                <h5 className="text-xs font-bold text-white mt-0.5">Human Approval & Escalation</h5>
                <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                  Routes directly into the SRE Investigation Workspace with proposed remediation steps, blast radius preview, and 1-click confirmation gates.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default ArchitectureSection;
