/**
 * frontend/src/components/landing/HowItWorksSection.jsx
 * 
 * Step-by-step operational lifecycle: 01 Detect -> 02 Understand -> 03 Predict -> 04 Decide -> 05 Remediate.
 */

import React from 'react';
import { Search, GitMerge, LineChart, CheckSquare, Wrench } from 'lucide-react';

export function HowItWorksSection() {
  const steps = [
    {
      num: '01',
      title: 'Detect',
      icon: Search,
      tag: 'Anomaly Isolation',
      desc: 'Ingests metrics, logs, and spans in real-time. Unsupervised ML models detect abnormal degradation before user-facing thresholds breach.',
    },
    {
      num: '02',
      title: 'Understand',
      icon: GitMerge,
      tag: 'Topological RCA',
      desc: 'Traverses the 12-node microservice dependency topology to distinguish symptoms from root causes and map blast radii.',
    },
    {
      num: '03',
      title: 'Predict',
      icon: LineChart,
      tag: 'Failure Forecasting',
      desc: 'Computes multi-factor risk scores and failure trajectory curves, giving engineering teams up to 18 minutes of proactive lead time.',
    },
    {
      num: '04',
      title: 'Decide',
      icon: CheckSquare,
      tag: 'Confidence Routing',
      desc: 'Categorizes incidents into confidence tiers: autonomous execution for proven remediations, or supervised SRE review for high-risk changes.',
    },
    {
      num: '05',
      title: 'Remediate',
      icon: Wrench,
      tag: 'Automated Recovery',
      desc: 'Dispatches targeted Ansible playbooks, restarts degraded connection pools, or scales container replicas with automated verification.',
    },
  ];

  return (
    <section id="how-it-works" className="py-24 relative">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs uppercase font-mono font-bold text-cyan-400 tracking-wider">
            Operational Lifecycle
          </span>
          <h2 className="text-3xl font-extrabold text-white mt-2 tracking-tight">
            How Synapse RiskOps Works
          </h2>
          <p className="text-sm text-slate-400 mt-3 leading-relaxed">
            From anomalous telemetry signals to verified self-healing recovery in five structured stages.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className="saas-card p-5 flex flex-col justify-between hover:border-slate-600 transition-all group"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xl font-black font-mono text-slate-600 group-hover:text-cyan-400 transition-colors">
                      {step.num}
                    </span>
                    <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 group-hover:text-white transition-colors">
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>
                  <h3 className="text-base font-bold text-white mb-1">{step.title}</h3>
                  <span className="text-[10px] font-mono text-indigo-400 uppercase tracking-wide block mb-2">
                    {step.tag}
                  </span>
                  <p className="text-xs text-slate-400 leading-relaxed">{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default HowItWorksSection;
