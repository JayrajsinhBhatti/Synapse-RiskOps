/**
 * frontend/src/components/landing/LandingHero.jsx
 * 
 * SaaS Hero section featuring an interactive abstract infrastructure network visualizer
 * depicting: Services -> Telemetry -> AI Detection -> Root Cause -> Risk -> Remediation.
 */

import React, { useState } from 'react';
import { ArrowRight, Play, ShieldAlert, Cpu, Activity, GitBranch, AlertTriangle, CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';

export function LandingHero({ onGetStarted, onSeeHowItWorks }) {
  const [activeStage, setActiveStage] = useState(2); // Default to AI Detection

  const stages = [
    {
      id: 0,
      name: 'Services',
      short: '01',
      icon: Cpu,
      title: 'Distributed Microservices',
      status: '12 Monitored Services',
      metric: 'API Gateway, Auth, Orders, Payment',
      color: 'from-blue-500 to-indigo-500',
      badge: 'Tier 1 Core',
    },
    {
      id: 1,
      name: 'Telemetry',
      short: '02',
      icon: Activity,
      title: 'Metrics & Trace Ingestion',
      status: 'P99 Latency & Error Rates',
      metric: 'Telemetry stream: 14,200 msg/sec',
      color: 'from-indigo-500 to-cyan-500',
      badge: 'Live Ingest',
    },
    {
      id: 2,
      name: 'AI Detection',
      short: '03',
      icon: AlertTriangle,
      title: 'Early Anomaly Detection',
      status: 'Z-Score & Isolation Forest',
      metric: 'Anomaly score 0.885 (Lead time +18m)',
      color: 'from-amber-500 to-orange-500',
      badge: 'AI Detection',
    },
    {
      id: 3,
      name: 'Root Cause',
      short: '04',
      icon: GitBranch,
      title: 'Graph Traversal (RCA)',
      status: 'NetworkX Dependency Analysis',
      metric: 'Blast radius isolated to Payment Gateway',
      color: 'from-rose-500 to-red-500',
      badge: 'Root Cause',
    },
    {
      id: 4,
      name: 'Risk',
      short: '05',
      icon: ShieldAlert,
      title: 'Composite Risk Assessment',
      status: 'Multi-factor Risk Score: 88.50',
      metric: 'Impact tier: Critical (Cascade Risk)',
      color: 'from-purple-500 to-indigo-500',
      badge: 'Risk Analysis',
    },
    {
      id: 5,
      name: 'Remediation',
      short: '06',
      icon: CheckCircle2,
      title: 'Automated Remediation',
      status: 'Ansible & Pod Re-scaling',
      metric: 'Remediation confidence 94% — MTTR 2m 14s',
      color: 'from-emerald-500 to-cyan-500',
      badge: 'Self-Healing',
    },
  ];

  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden">
      {/* Background glow highlights */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-indigo-600/15 blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute top-1/3 left-1/3 w-[300px] h-[250px] bg-cyan-500/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 relative z-10 text-center">
        {/* Top Announcement Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-xs font-medium mb-8 hover:bg-indigo-500/15 transition-all cursor-pointer">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>Synapse RiskOps 2.0 — Autonomous Incident Intelligence</span>
          <ArrowRight className="w-3.5 h-3.5 text-indigo-400 ml-0.5" />
        </div>

        {/* Main Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-[1.12] max-w-4xl mx-auto">
          Turn infrastructure signals into{' '}
          <span className="gradient-brand">intelligent action</span>.
        </h1>

        {/* Supporting Text */}
        <p className="mt-6 text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
          Synapse RiskOps combines anomaly detection, failure prediction, root-cause analysis
          and intelligent remediation into one operational control center.
        </p>

        {/* CTA Buttons */}
        <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3.5">
          <Button
            variant="cyan"
            size="lg"
            onClick={onGetStarted}
            iconRight={ArrowRight}
            className="w-full sm:w-auto text-sm"
          >
            Get Started
          </Button>
          <Button
            variant="secondary"
            size="lg"
            onClick={onSeeHowItWorks}
            icon={Play}
            className="w-full sm:w-auto text-sm"
          >
            See How It Works
          </Button>
        </div>

        {/* Interactive Abstract Infrastructure Network Visualizer */}
        <div className="mt-16 saas-card p-6 md:p-8 text-left relative overflow-hidden shadow-2xl shadow-indigo-950/40">
          {/* Top Bar of the Visualizer */}
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 mb-6 border-b border-white/10 gap-3">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-cyan-400 font-semibold block">
                Interactive Operational Pipeline
              </span>
              <h3 className="text-base font-bold text-white mt-0.5">
                End-to-End Infrastructure Risk Traversal
              </h3>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Simulated Signal Stream: ONLINE</span>
            </div>
          </div>

          {/* Stepper Node Ribbon */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mb-6">
            {stages.map((stage) => {
              const Icon = stage.icon;
              const isSelected = activeStage === stage.id;
              return (
                <button
                  key={stage.id}
                  onClick={() => setActiveStage(stage.id)}
                  className={`p-3 rounded-xl border text-left transition-all duration-150 relative ${
                    isSelected
                      ? 'bg-slate-800/90 border-indigo-400 shadow-md shadow-indigo-500/15 ring-1 ring-indigo-400/40'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono text-slate-400">{stage.short}</span>
                    <Icon
                      className={`w-4 h-4 ${
                        isSelected ? 'text-cyan-400' : 'text-slate-400'
                      }`}
                    />
                  </div>
                  <div className="text-xs font-bold text-white truncate">{stage.name}</div>
                  <div className="text-[10px] text-slate-400 truncate mt-0.5">{stage.badge}</div>
                </button>
              );
            })}
          </div>

          {/* Detailed Stage Preview Box */}
          <div className="rounded-xl bg-slate-950/80 border border-slate-800 p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono uppercase tracking-wide text-cyan-400 font-semibold">
                  Stage {stages[activeStage].short} — {stages[activeStage].title}
                </span>
              </div>
              <div className="text-sm font-semibold text-white">
                {stages[activeStage].status}
              </div>
              <div className="text-xs text-slate-300 font-mono">
                {stages[activeStage].metric}
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={onGetStarted}
                iconRight={ArrowRight}
                className="text-xs"
              >
                Inspect in Live Cockpit
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default LandingHero;
