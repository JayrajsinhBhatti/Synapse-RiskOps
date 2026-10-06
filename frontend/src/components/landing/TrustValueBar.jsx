/**
 * frontend/src/components/landing/TrustValueBar.jsx
 * 
 * High-clarity Trust Value Bar highlighting core architectural promises.
 */

import React from 'react';
import { Activity, GitBranch, ShieldCheck } from 'lucide-react';

export function TrustValueBar() {
  const values = [
    {
      icon: Activity,
      title: 'REAL-TIME INCIDENT INTELLIGENCE',
      subtitle: 'Sub-second anomaly ingestion via Server-Sent Events & OpenTelemetry',
    },
    {
      icon: GitBranch,
      title: 'AI-POWERED ROOT CAUSE ANALYSIS',
      subtitle: 'Graph traversal & causal inference over microservice dependency trees',
    },
    {
      icon: ShieldCheck,
      title: 'RISK-AWARE REMEDIATION',
      subtitle: 'Automated Ansible playbooks with human-in-the-loop confidence gates',
    },
  ];

  return (
    <section className="border-y border-white/5 bg-slate-950/40 py-10 relative">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
          {values.map((v, i) => {
            const Icon = v.icon;
            return (
              <div key={i} className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0 text-cyan-400">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold font-mono tracking-wider text-slate-200 uppercase">
                    {v.title}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    {v.subtitle}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default TrustValueBar;
