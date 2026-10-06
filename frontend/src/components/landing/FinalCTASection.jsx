/**
 * frontend/src/components/landing/FinalCTASection.jsx
 * 
 * High-impact final call to action section.
 */

import React from 'react';
import { ArrowRight, ShieldCheck, Zap } from 'lucide-react';
import Button from '../common/Button';

export function FinalCTASection({ onGetStarted }) {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="max-w-5xl mx-auto px-6 relative z-10">
        <div className="rounded-3xl bg-gradient-to-b from-indigo-950/60 to-slate-950 border border-indigo-500/30 p-10 md:p-16 text-center relative overflow-hidden shadow-2xl shadow-indigo-950/50">
          {/* Subtle decorative glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[200px] bg-indigo-500/20 blur-[100px] pointer-events-none rounded-full" />

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-mono mb-6">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            <span>Operational Excellence</span>
          </div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight max-w-3xl mx-auto leading-tight">
            Know what failed. Understand why.{' '}
            <span className="gradient-brand">Act before it spreads.</span>
          </h2>

          <p className="mt-5 text-sm sm:text-base text-slate-300 max-w-xl mx-auto leading-relaxed">
            Eliminate alert fatigue and turn cascade outages into automated, risk-governed recoveries.
          </p>

          <div className="mt-8 flex justify-center">
            <Button
              variant="cyan"
              size="lg"
              onClick={onGetStarted}
              iconRight={ArrowRight}
              className="text-sm font-bold px-8 shadow-glow-cyan"
            >
              Get Started Now
            </Button>
          </div>

          <div className="mt-8 flex items-center justify-center gap-6 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> PostgreSQL & JWT Secured
            </span>
            <span className="flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-cyan-400" /> Zero Infrastructure Agent Overhead
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

export default FinalCTASection;
