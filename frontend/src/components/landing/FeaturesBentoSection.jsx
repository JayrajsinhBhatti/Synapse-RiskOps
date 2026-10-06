/**
 * frontend/src/components/landing/FeaturesBentoSection.jsx
 * 
 * Bento-grid capabilities section inspired by user UI code.
 * Features 4 highly-polished interactive cards:
 * 1. GNN Causal Propagation & Dependency Graph
 * 2. Context-Aware ML Risk Forecasting
 * 3. Autonomous Workflow & Playbook Orchestrator
 * 4. Real-time Telemetry & Anomaly Waveform Analytics
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  Wand2,
  Rocket,
  Settings,
  Zap,
  Flame,
  Check,
  Activity,
  Layers,
  Network,
  ShieldCheck,
  Server,
  RefreshCw,
  GitBranch,
} from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

export default function FeaturesBentoSection({ className }) {
  return (
    <section id="features" className={"w-full px-6 py-28 dark:bg-slate-950 bg-slate-50 font-sans relative overflow-hidden transition-colors duration-300 " + (className || '')}>
      {/* Decorative Gradient Glows */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-[140px] -translate-y-1/2 pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[450px] h-[450px] bg-cyan-500/10 rounded-full blur-[140px] translate-y-1/2 pointer-events-none" />

      {/* Section Header */}
      <div className="max-w-6xl mx-auto relative z-10 mb-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 dark:text-indigo-400 text-xs font-mono font-semibold mb-4"
        >
          <SparkleIcon />
          <span>Core AI & Orchestration Engine</span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
          viewport={{ once: true }}
          className="text-3xl md:text-5xl font-bold dark:text-white text-slate-900 mb-5 leading-[1.15]"
          style={{ fontFamily: "'Chakra Petch', sans-serif" }}
        >
          Explore the Power of <br />
          <span className="bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-500 dark:from-cyan-400 dark:via-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
            Synapse RiskOps AI
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
          viewport={{ once: true }}
          className="text-base dark:text-slate-400 text-slate-600 max-w-2xl mx-auto leading-relaxed"
        >
          Scale your cloud reliability with an AIOps copilot that understands microservice topology,
          predicts downstream cascading failures, and mitigates risks with zero manual toil.
        </motion.p>
      </div>

      {/* Bento Grid */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl mx-auto relative z-10"
      >
        {/* ROW 1 - Card 1: GNN Causal Propagation */}
        <motion.div
          variants={cardVariants}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
          className="rounded-[32px] border dark:border-white/10 border-slate-200/90 dark:bg-slate-900/60 bg-white/90 backdrop-blur-xl p-7 flex flex-col justify-between group transition-all relative overflow-hidden min-h-[460px] shadow-2xl dark:shadow-black/50 shadow-slate-200/60"
        >
          {/* Subtle Ambient Radial Glow */}
          <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <span className="text-[11px] font-mono font-bold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider block mb-2">
              Graph Neural Reasoning
            </span>
            <h3
              className="text-2xl md:text-3xl font-bold dark:text-white text-slate-900 leading-tight tracking-tight"
              style={{ fontFamily: "'Chakra Petch', sans-serif" }}
            >
              Causal Graph Traversal, <br />
              <span className="text-cyan-500 dark:text-cyan-400 italic">Instant Root Isolation.</span>
            </h3>
            <p className="text-xs md:text-sm dark:text-slate-300 text-slate-600 leading-relaxed max-w-md mt-2.5">
              Traverse directional microservice meshes in real-time to pinpoint upstream root causes rather than getting flooded with downstream alert storms.
            </p>
          </div>

          {/* Interactive Chips Preview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 relative z-10 mt-8">
            <div className="p-4 rounded-2xl dark:bg-white/[0.04] bg-slate-50/80 backdrop-blur-md border dark:border-white/10 border-slate-200 hover:border-cyan-500/40 transition-all flex flex-col gap-2">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-500 dark:text-cyan-400 shrink-0">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-bold dark:text-white text-slate-900 block">Dependency Graph</span>
                <p className="text-[11px] dark:text-slate-400 text-slate-500 leading-normal mt-0.5">
                  Topology-aware blast radius isolation across Kubernetes pods.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl dark:bg-white/[0.04] bg-slate-50/80 backdrop-blur-md border dark:border-white/10 border-slate-200 hover:border-indigo-500/40 transition-all flex flex-col gap-2">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500 dark:text-indigo-400 shrink-0">
                <GitBranch className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-bold dark:text-white text-slate-900 block">Root Cause Chain</span>
                <p className="text-[11px] dark:text-slate-400 text-slate-500 leading-normal mt-0.5">
                  Synthesizes Alert → Origin → Risk → Remediation chain.
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ROW 1 - Card 2: Adaptive ML Risk Forecasting */}
        <motion.div
          variants={cardVariants}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
          className="rounded-[32px] border dark:border-white/10 border-slate-200/90 dark:bg-slate-900/60 bg-white/90 backdrop-blur-xl p-7 flex flex-col justify-between overflow-hidden relative min-h-[460px] shadow-2xl dark:shadow-black/50 shadow-slate-200/60"
        >
          <div className="absolute top-1/4 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-[90px] pointer-events-none" />

          {/* Glass Mockup Inside Card */}
          <div className="relative z-10 w-full flex-1 flex flex-col items-center justify-center py-4">
            <div className="w-full max-w-[300px] dark:bg-slate-950/70 bg-slate-50/90 backdrop-blur-2xl border dark:border-white/10 border-slate-200 rounded-2xl p-5 shadow-2xl space-y-3">
              <div className="text-[10px] font-mono dark:text-slate-400 text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-between">
                <span>Adaptive Risk Tiers</span>
                <span className="text-emerald-500 dark:text-emerald-400">Model v1.4</span>
              </div>

              {[
                { label: 'Tier 1: Autonomous Remediation', score: '96% Conf', color: 'bg-emerald-400', border: 'dark:border-emerald-500/30 border-emerald-500/40' },
                { label: 'Tier 2: Supervised SRE Approval', score: '78% Conf', color: 'bg-amber-400', border: 'dark:border-amber-500/30 border-amber-500/40' },
                { label: 'Tier 3: Manual Incident Escalation', score: '42% Conf', color: 'bg-rose-400', border: 'dark:border-rose-500/30 border-rose-500/40' },
              ].map((tier, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className={`flex items-center justify-between dark:bg-white/[0.03] bg-white rounded-xl p-2.5 border ${tier.border} text-xs shadow-sm`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${tier.color}`} />
                    <span className="font-semibold dark:text-slate-200 text-slate-800 text-[11px]">{tier.label}</span>
                  </div>
                  <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500">{tier.score}</span>
                </motion.div>
              ))}

              {/* Streaming Data Indicator */}
              <div className="mt-4 dark:bg-slate-900/90 bg-white rounded-full border dark:border-white/10 border-slate-200 p-2 flex items-center gap-2.5 shadow-sm">
                <div className="w-5 h-5 rounded-full border-2 border-cyan-400/30 border-t-cyan-400 animate-spin shrink-0" />
                <span className="text-[10px] font-mono dark:text-slate-300 text-slate-600 flex-1 truncate">
                  Scraping Prometheus metrics...
                </span>
                <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center shrink-0">
                  <Wand2 className="w-3 h-3 text-white" />
                </div>
              </div>
            </div>
          </div>

          <div className="relative z-10 pt-4">
            <h3
              className="text-xl md:text-2xl font-bold dark:text-white text-slate-900 tracking-tight"
              style={{ fontFamily: "'Chakra Petch', sans-serif" }}
            >
              Context-Aware Risk Prediction
            </h3>
            <p className="text-xs md:text-sm dark:text-slate-400 text-slate-600 leading-relaxed mt-1.5">
              The platform evaluates continuous telemetry drift against 30-day baseline sliding windows to forecast SLA violations 5-10 minutes ahead.
            </p>
          </div>
        </motion.div>

        {/* ROW 2 - Card 3: Automated SRE Workflow Builder */}
        <motion.div
          variants={cardVariants}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
          className="rounded-[32px] border dark:border-white/10 border-slate-200/90 dark:bg-slate-900/60 bg-white/90 backdrop-blur-xl overflow-hidden flex flex-col justify-between shadow-2xl dark:shadow-black/50 shadow-slate-200/60"
        >
          {/* Visual Interactive Pipeline Canvas */}
          <div className="h-72 relative flex items-center justify-center border-b dark:border-white/10 border-slate-200 p-6 overflow-hidden dark:bg-slate-950/60 bg-slate-50/80">
            <div className="relative z-10 w-full max-w-[280px] flex flex-col items-center">
              {/* Trigger Node */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                className="dark:bg-slate-900 bg-white rounded-2xl p-3 border border-rose-500/30 flex items-center gap-3 w-full mb-6 relative shadow-lg shadow-rose-500/10"
              >
                <div className="w-9 h-9 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-500 dark:text-rose-400 shrink-0">
                  <Zap className="w-4 h-4" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[11px] font-bold dark:text-white text-slate-900 font-mono">Alert: High Inbound Latency</span>
                  <span className="text-[9px] dark:text-slate-400 text-slate-500 font-mono">p99 &gt; 1200ms on payment-service</span>
                </div>
                {/* Connecting Line Down */}
                <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 w-px h-6 bg-gradient-to-b from-rose-400/50 to-cyan-400/50" />
              </motion.div>

              {/* Action Nodes Grid */}
              <div className="grid grid-cols-2 gap-3 w-full relative">
                <div className="p-2.5 rounded-xl dark:bg-slate-900/90 bg-white border dark:border-white/10 border-slate-200 shadow-sm flex flex-col gap-1 items-center text-center">
                  <div className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center">
                    <Settings className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[10px] font-bold dark:text-white text-slate-900 font-mono">K8s Scale Pods</span>
                </div>

                <div className="p-2.5 rounded-xl dark:bg-slate-900/90 bg-white border dark:border-white/10 border-slate-200 shadow-sm flex flex-col gap-1 items-center text-center">
                  <div className="w-7 h-7 rounded-lg bg-cyan-500/20 text-cyan-500 dark:text-cyan-400 flex items-center justify-center">
                    <RefreshCw className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-[10px] font-bold dark:text-white text-slate-900 font-mono">Recycle Pool</span>
                </div>
              </div>

              {/* Success Indicator */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="mt-6 bg-emerald-500/20 border border-emerald-500/40 text-emerald-600 dark:text-emerald-300 text-[10px] font-mono font-bold py-1.5 px-4 rounded-full flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
              >
                <Check className="w-3.5 h-3.5 stroke-[3] text-emerald-500 dark:text-emerald-400" />
                <span>Playbook Executed • Status RESOLVED</span>
              </motion.div>
            </div>
          </div>

          <div className="p-7">
            <h3
              className="text-xl md:text-2xl font-bold dark:text-white text-slate-900 tracking-tight"
              style={{ fontFamily: "'Chakra Petch', sans-serif" }}
            >
              Automated Runbooks & Remediation
            </h3>
            <p className="text-xs md:text-sm dark:text-slate-400 text-slate-600 leading-relaxed mt-1.5">
              Trigger audited remediation playbooks directly through backend workers: horizontal scaling, thread dumps, and connection recycling.
            </p>
          </div>
        </motion.div>

        {/* ROW 2 - Card 4: Real-time Telemetry & Waveform Analytics */}
        <motion.div
          variants={cardVariants}
          whileHover={{ y: -4, transition: { duration: 0.2 } }}
          className="rounded-[32px] border dark:border-white/10 border-slate-200/90 dark:bg-slate-900/60 bg-white/90 backdrop-blur-xl overflow-hidden flex flex-col justify-between shadow-2xl dark:shadow-black/50 shadow-slate-200/60"
        >
          {/* Animated Telemetry Waveform Mockup */}
          <div className="h-72 relative flex flex-col justify-center border-b dark:border-white/10 border-slate-200 p-6 dark:bg-slate-950/60 bg-slate-50/80">
            <div className="w-full h-full dark:bg-slate-900/80 bg-white rounded-2xl border dark:border-white/10 border-slate-200 p-5 flex flex-col justify-between shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-rose-500/20 flex items-center justify-center text-rose-500 dark:text-rose-400">
                    <Flame className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-bold dark:text-white text-slate-900 block">Cluster Telemetry Stream</span>
                    <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500">SSE Active • Sub-second delay</span>
                  </div>
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-500 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  LIVE STREAM
                </span>
              </div>

              {/* Dynamic Waveform Bars */}
              <div className="flex items-end gap-2 h-24 px-2">
                {[35, 60, 45, 88, 70, 95, 55, 65, 40, 75, 50, 85].map((h, i) => (
                  <div key={i} className="flex-1 dark:bg-slate-800/60 bg-slate-100 rounded-t-sm h-full flex flex-col justify-end">
                    <motion.div
                      animate={{ height: [`${h * 0.4}%`, `${h}%`, `${h * 0.5}%`] }}
                      transition={{ duration: 2.2 + (i % 3) * 0.4, repeat: Infinity, ease: 'easeInOut' }}
                      className={`w-full rounded-t-sm ${
                        h > 80 ? 'bg-gradient-to-t from-rose-500 to-amber-400' : 'bg-gradient-to-t from-indigo-500 to-cyan-400'
                      }`}
                    />
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between text-[10px] font-mono dark:text-slate-500 text-slate-400 pt-2 border-t dark:border-white/[0.06] border-slate-200">
                <span>Ingest: 142k events/sec</span>
                <span className="text-cyan-500 dark:text-cyan-400 font-semibold">99.98% Anomaly Precision</span>
              </div>
            </div>
          </div>

          <div className="p-7">
            <h3
              className="text-xl md:text-2xl font-bold dark:text-white text-slate-900 tracking-tight"
              style={{ fontFamily: "'Chakra Petch', sans-serif" }}
            >
              Real-Time Conversational Insights
            </h3>
            <p className="text-xs md:text-sm dark:text-slate-400 text-slate-600 leading-relaxed mt-1.5">
              Audit incidents as they happen with SSE streaming and interact with Jayraj's integrated AI Ops Chatbot for instant telemetry queries.
            </p>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}

function SparkleIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  );
}
