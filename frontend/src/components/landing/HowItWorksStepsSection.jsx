/**
 * frontend/src/components/landing/HowItWorksStepsSection.jsx
 * 
 * 3-Step Autonomous RiskOps Architecture journey.
 * Implements user's HowItWorks01Kelo template with:
 * - Scanning light line animation
 * - Radar ripple wave animation
 * - Live bar chart visualization
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  Database,
  BarChart2,
  CheckCircle,
  Activity,
  ArrowRight,
  ShieldCheck,
  Zap,
} from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.18,
    },
  },
};

const stepVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.7,
      ease: [0.21, 0.47, 0.32, 0.98],
    },
  },
};

export default function HowItWorksStepsSection({ onGetStarted, className }) {
  return (
    <section id="how-it-works" className={"w-full px-6 md:px-12 lg:px-20 py-24 dark:bg-slate-950 bg-slate-50 relative overflow-hidden transition-colors duration-300 " + (className || '')}>
      {/* Background Glows */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden">
        <motion.div
          animate={{
            y: [0, -20, 0],
            rotate: [0, 5, 0],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -top-24 -left-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            y: [0, 20, 0],
            rotate: [0, -5, 0],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
          className="absolute -bottom-24 -right-24 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl"
        />
      </div>

      {/* Section Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
        viewport={{ once: true }}
        className="text-center mb-16 flex flex-col items-center gap-3 relative z-10"
      >
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-500/20">
          Self-Healing Pipeline
        </span>

        <h2
          className="font-bold text-3xl md:text-5xl dark:text-white text-slate-900 text-center leading-[1.1] max-w-2xl"
          style={{ fontFamily: "'Chakra Petch', sans-serif" }}
        >
          Transform Cloud Reliability <br />
          <span className="bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-500 dark:from-cyan-400 dark:via-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
            in 3 Autonomous Steps
          </span>
        </h2>
        <p className="text-sm md:text-base dark:text-slate-400 text-slate-600 max-w-xl">
          From microservice telemetry ingestion to AI causal diagnosis and audited playbook execution.
        </p>
      </motion.div>

      {/* 3 Step Cards Grid */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16 max-w-6xl mx-auto relative z-10"
      >
        {/* STEP 01: Telemetry Ingestion & Mapping */}
        <motion.div variants={stepVariants} className="flex flex-col gap-6 group">
          <div className="rounded-2xl overflow-hidden relative aspect-[4/3] w-full shadow-2xl dark:shadow-black/40 shadow-slate-200/80 border dark:border-white/10 border-slate-200 dark:bg-slate-900/80 bg-white">
            {/* Visual Glass Chips Inside Mockup */}
            <div className="absolute inset-0 flex items-center justify-center p-6 bg-gradient-to-br dark:from-indigo-950/40 dark:via-slate-900/60 dark:to-slate-950 from-indigo-50/50 via-slate-50 to-white">
              <div className="w-full h-full dark:bg-slate-950/60 bg-white/90 backdrop-blur-xl rounded-xl border dark:border-white/10 border-slate-200 p-4 flex flex-col justify-center gap-2.5 overflow-hidden shadow-sm">
                {/* Chip 1: Metric Ingest */}
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="dark:bg-white/[0.04] bg-slate-50 backdrop-blur-md rounded-lg border dark:border-white/10 border-slate-200 px-2.5 py-1.5 flex items-center gap-2 shadow-sm"
                >
                  <div className="w-6 h-6 rounded-md bg-indigo-500/20 flex items-center justify-center shrink-0">
                    <Database className="h-3 w-3 text-indigo-500 dark:text-indigo-400" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold dark:text-white text-slate-900 font-mono leading-none">OTel & PromQL Scrape</span>
                    <span className="text-[8px] dark:text-slate-400 text-slate-500 leading-none mt-0.5">Continuous telemetry ingestion</span>
                  </div>
                </motion.div>

                {/* Chip 2: Process Analysis (Active with light sweep scan) */}
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.35 }}
                  className="relative dark:bg-slate-900 bg-white rounded-lg px-2.5 py-2 flex items-center gap-2.5 shadow-xl border border-cyan-500/40 overflow-hidden"
                >
                  {/* Scanning Light Line Animation */}
                  <motion.div
                    animate={{ x: ['-100%', '200%'] }}
                    transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
                    className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-cyan-400/25 to-transparent -skew-x-12 pointer-events-none"
                  />

                  <div className="w-7 h-7 rounded-md bg-cyan-500/20 flex items-center justify-center shrink-0">
                    <BarChart2 className="h-3.5 w-3.5 text-cyan-500 dark:text-cyan-400" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold dark:text-white text-slate-900 font-mono leading-none">Graph Topology Mapping</span>
                    <span className="text-[8px] dark:text-slate-400 text-slate-500 leading-none mt-1">Directed dependency resolution</span>
                  </div>
                </motion.div>

                {/* Chip 3: Anomaly Detected */}
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 }}
                  className="dark:bg-white/[0.04] bg-slate-50 backdrop-blur-md rounded-lg border dark:border-white/10 border-slate-200 px-2.5 py-1.5 flex items-center gap-2 shadow-sm"
                >
                  <div className="w-6 h-6 rounded-md bg-emerald-500/20 flex items-center justify-center shrink-0">
                    <CheckCircle className="h-3 w-3 text-emerald-500 dark:text-emerald-400" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold dark:text-white text-slate-900 font-mono leading-none">Baseline Deviation Check</span>
                    <span className="text-[8px] dark:text-slate-400 text-slate-500 leading-none mt-0.5">Normal behavior verified</span>
                  </div>
                </motion.div>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <span className="inline-flex w-fit rounded-full text-indigo-500 dark:text-indigo-400 text-xs font-mono font-bold px-2.5 py-0.5 border border-indigo-500/30 bg-indigo-500/10">
              Step 01
            </span>
            <h3 className="text-xl font-bold dark:text-white text-slate-900 leading-tight">
              Ingest & Map Dependencies
            </h3>
            <p className="text-sm dark:text-slate-400 text-slate-600 leading-relaxed">
              Connect your Prometheus and OpenTelemetry agents — our engine auto-maps microservice topology and dependencies.
            </p>
          </div>
        </motion.div>

        {/* STEP 02: AI Causal Diagnosis */}
        <motion.div variants={stepVariants} className="flex flex-col gap-6 group">
          <div className="rounded-2xl overflow-hidden relative aspect-[4/3] w-full shadow-2xl dark:shadow-black/40 shadow-slate-200/80 border dark:border-white/10 border-slate-200 dark:bg-slate-900/80 bg-white">
            {/* Radar Ripple Waves Animation */}
            <div className="absolute inset-0 flex items-center justify-center p-6 bg-gradient-to-br dark:from-indigo-950/40 dark:via-slate-900/60 dark:to-slate-950 from-indigo-50/50 via-slate-50 to-white">
              <div className="w-full h-full dark:bg-slate-950/60 bg-white/90 backdrop-blur-xl rounded-xl border dark:border-white/10 border-slate-200 p-4 flex items-center justify-between overflow-hidden shadow-sm">
                {/* Left: Concentric Radar Ripples */}
                <div className="relative w-1/2 h-full flex items-center justify-center">
                  <div className="relative w-28 h-28 flex items-center justify-center">
                    {/* Glowing Center Point */}
                    <motion.div
                      animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                      className="w-3.5 h-3.5 rounded-full bg-cyan-500 dark:bg-cyan-400 shadow-[0_0_15px_#22d3ee] z-10"
                    />

                    {/* Dynamic Ripples */}
                    {[1, 2, 3, 4].map((i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, scale: 0.2 }}
                        animate={{
                          scale: [0.2, 1.6],
                          opacity: [0, 0.6, 0],
                        }}
                        transition={{
                          duration: 3.5,
                          repeat: Infinity,
                          ease: 'easeOut',
                          delay: i * 0.7,
                        }}
                        className="absolute border border-cyan-400/40 rounded-full"
                        style={{ width: '100%', height: '100%' }}
                      />
                    ))}
                  </div>
                </div>

                {/* Right: Action Pills */}
                <div className="flex flex-col gap-2 items-end pr-1 font-mono text-[10px]">
                  {['Diagnose Root', 'Predict Blast', 'Route Playbook'].map((text, i) => (
                    <motion.div
                      key={text}
                      initial={{ opacity: 0, x: 10 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.1 }}
                      className={`rounded-lg px-3 py-1.5 border flex items-center justify-center font-bold ${
                        i === 1
                          ? 'bg-cyan-500 text-white dark:text-slate-950 border-cyan-400 shadow-md'
                          : 'dark:bg-slate-900 bg-slate-100 dark:text-slate-300 text-slate-700 dark:border-white/10 border-slate-200'
                      }`}
                    >
                      {text}
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <span className="inline-flex w-fit rounded-full text-cyan-600 dark:text-cyan-400 text-xs font-mono font-bold px-2.5 py-0.5 border border-cyan-500/30 bg-cyan-500/10">
              Step 02
            </span>
            <h3 className="text-xl font-bold dark:text-white text-slate-900 leading-tight">
              Evaluate Risk & Isolate RCA
            </h3>
            <p className="text-sm dark:text-slate-400 text-slate-600 leading-relaxed">
              RiskEngine assigns risk scores (0-100) and executes graph traversal to pinpoint the root service before downstream cascade occurs.
            </p>
          </div>
        </motion.div>

        {/* STEP 03: Autonomous Remediation */}
        <motion.div variants={stepVariants} className="flex flex-col gap-6 group">
          <div className="rounded-2xl overflow-hidden relative aspect-[4/3] w-full shadow-2xl dark:shadow-black/40 shadow-slate-200/80 border dark:border-white/10 border-slate-200 dark:bg-slate-900/80 bg-white">
            {/* Live Chart Visualization Mockup */}
            <div className="absolute inset-0 flex items-center justify-center p-6 bg-gradient-to-br dark:from-indigo-950/40 dark:via-slate-900/60 dark:to-slate-950 from-indigo-50/50 via-slate-50 to-white">
              <div className="w-full h-full dark:bg-slate-950/60 bg-white/90 backdrop-blur-xl rounded-xl border dark:border-white/10 border-slate-200 p-4 flex flex-col justify-center gap-3 overflow-hidden shadow-sm">
                {/* Main Card with Animated Mini Bars */}
                <div className="dark:bg-slate-900 bg-slate-50 rounded-lg p-2.5 flex items-center gap-2.5 border dark:border-white/10 border-slate-200 relative overflow-hidden">
                  <div className="w-8 h-8 rounded-md bg-emerald-500/20 flex items-center justify-center shrink-0">
                    <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
                  </div>

                  {/* Mini Bars */}
                  <div className="flex-1 flex items-end gap-1 h-7 px-1">
                    {[4, 8, 12, 6, 10, 8, 7, 6, 9, 5].map((h, i) => (
                      <motion.div
                        key={i}
                        initial={{ height: 0 }}
                        whileInView={{
                          height: [`${h * 1.5}px`, `${h * 2.2}px`, `${h * 1.5}px`],
                        }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                          ease: 'easeInOut',
                          delay: i * 0.05,
                        }}
                        className="w-1.5 bg-emerald-500/50 rounded-sm"
                      />
                    ))}
                  </div>

                  <span className="text-[9px] font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    99.9%
                  </span>
                </div>

                {/* Bottom Pill */}
                <div className="dark:bg-slate-900 bg-white rounded-lg px-3 py-1.5 w-fit border border-emerald-500/30 flex items-center gap-2 shadow-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-300 font-bold">
                    Ansible Playbook Executed
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <span className="inline-flex w-fit rounded-full text-emerald-600 dark:text-emerald-400 text-xs font-mono font-bold px-2.5 py-0.5 border border-emerald-500/30 bg-emerald-500/10">
              Step 03
            </span>
            <h3 className="text-xl font-bold dark:text-white text-slate-900 leading-tight">
              Remediate & Audit in Real-Time
            </h3>
            <p className="text-sm dark:text-slate-400 text-slate-600 leading-relaxed">
              Confidence Router triggers safe runbooks (K8s pod scale-out, pool recycle) and broadcasts live audit updates over Server-Sent Events.
            </p>
          </div>
        </motion.div>
      </motion.div>

      {/* CTA Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        viewport={{ once: true }}
        className="flex flex-col sm:flex-row items-center justify-center gap-4 relative z-10"
      >
        <button
          onClick={onGetStarted}
          className="rounded-full px-8 py-3.5 text-xs font-bold tracking-wider uppercase bg-gradient-to-r from-indigo-500 to-cyan-500 text-white shadow-xl shadow-indigo-500/25 hover:brightness-110 transition-all"
        >
          Get Started with Synapse RiskOps
        </button>
      </motion.div>
    </section>
  );
}
