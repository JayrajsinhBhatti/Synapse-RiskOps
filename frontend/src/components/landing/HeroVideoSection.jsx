/**
 * frontend/src/components/landing/HeroVideoSection.jsx
 * 
 * High-performance Video Hero Section with Glassmorphic Navigation
 * and framer-motion micro-interactions.
 * Powered by local background video: /gemini_generated_video_a62a1b95.mp4
 */

import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Zap, ShieldCheck, ArrowRight, Play, Terminal, Activity, Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export default function HeroVideoSection({ onSignIn, onGetStarted, onLaunchApp }) {
  const videoRef = useRef(null);
  const { theme, toggleTheme, isDark } = useTheme();

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = 0.65;
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // Auto-play was prevented by browser policy until interaction
        });
      }
    }
  }, []);

  const handleAction = () => {
    if (onGetStarted) onGetStarted();
    else if (onLaunchApp) onLaunchApp();
    else if (onSignIn) onSignIn();
  };

  const stackLogos = [
    { name: 'Kubernetes', label: 'K8s Cluster' },
    { name: 'Prometheus', label: 'PromQL Telemetry' },
    { name: 'OpenTelemetry', label: 'OTel Tracing' },
    { name: 'Datadog', label: 'APM Metrics' },
    { name: 'AWS Cloud', label: 'EKS Cloud' },
    { name: 'Apache Kafka', label: 'Event Streaming' },
    { name: 'Grafana', label: 'Observability' },
    { name: 'PostgreSQL', label: 'State Store' },
  ];

  return (
    <section className="min-h-[105vh] flex flex-col bg-slate-950 relative w-full overflow-hidden">
      {/* Video Background - High Visibility */}
      <video
        ref={videoRef}
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 w-full h-full object-cover z-0 opacity-90 scale-100"
      >
        <source src="/gemini_generated_video_a62a1b95.mp4" type="video/mp4" />
      </video>

      {/* Dark Overlay to give high contrast for crisp white text while preserving video visibility */}
      <div className="absolute inset-0 bg-black/40 z-[1]" />
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t dark:from-slate-950 from-slate-950/60 to-transparent z-[1]" />

      {/* Floating Pill Navigation Bar */}
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="relative z-50 px-4 md:px-8 pt-6 pb-2"
      >
        <div className="max-w-5xl mx-auto flex items-center justify-between p-2 md:p-2.5 rounded-full dark:bg-slate-900/70 bg-white/90 backdrop-blur-2xl border dark:border-white/10 border-slate-200/80 shadow-2xl dark:shadow-black/40 shadow-slate-300/40 transition-colors duration-300">
          {/* Logo */}
          <div className="flex-1 flex items-center pl-3 flex-shrink-0">
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={handleAction}>
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <div className="flex items-center tracking-tight font-black text-sm dark:text-white text-slate-900">
                Synapse<span className="text-cyan-500 ml-1 font-semibold">RiskOps</span>
              </div>
            </div>
          </div>

          {/* Links */}
          <div className="hidden md:flex items-center gap-8 flex-shrink-0">
            {[
              { label: 'Capabilities', href: '#features' },
              { label: 'How It Works', href: '#how-it-works' },
              { label: 'Integrations', href: '#integrations' },
              { label: 'FAQ', href: '#faq' },
            ].map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="text-xs font-semibold dark:text-slate-300 dark:hover:text-white text-slate-700 hover:text-slate-950 transition-colors relative group tracking-wide"
              >
                {item.label}
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-300 group-hover:w-full" />
              </a>
            ))}
          </div>

          {/* Nav CTAs & Dark/Light Toggle */}
          <div className="flex-1 flex items-center justify-end gap-2 flex-shrink-0 whitespace-nowrap pr-1">
            {/* Dark / Light Mode Toggle Button */}
            <button
              onClick={toggleTheme}
              title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle Theme"
              className="p-2 rounded-full dark:text-slate-300 text-slate-700 hover:bg-slate-200/70 dark:hover:bg-white/10 transition-colors flex items-center justify-center"
            >
              {isDark ? (
                <Sun className="w-4 h-4 text-amber-300 hover:rotate-45 transition-transform duration-300" />
              ) : (
                <Moon className="w-4 h-4 text-indigo-600 hover:-rotate-12 transition-transform duration-300" />
              )}
            </button>

            <button
              onClick={onSignIn}
              className="text-xs font-bold dark:text-slate-300 text-slate-700 dark:hover:text-white hover:text-slate-950 transition-colors px-3 py-1.5 rounded-full hover:bg-slate-200/50 dark:hover:bg-white/5"
            >
              Sign In
            </button>
            <button
              onClick={handleAction}
              className="rounded-full px-4 py-2 text-xs font-bold dark:bg-white dark:text-slate-950 bg-slate-900 text-white hover:bg-slate-800 dark:hover:bg-slate-100 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-black/10 flex items-center gap-1.5"
            >
              <span>Launch App</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Hero Content */}
      <div className="relative flex-1 flex flex-col items-center justify-center text-center px-6 pt-16 md:pt-24 pb-16 z-10">
        <div className="flex flex-col items-center w-full max-w-4xl mx-auto">
          {/* Status Badge with Pure High-Contrast White Styling */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-black/55 backdrop-blur-md border border-white/20 text-white text-xs font-medium mb-6 shadow-2xl"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="font-mono text-[11px] text-cyan-400 font-bold uppercase tracking-wider">
              Autonomous RiskOps v0.6.0
            </span>
            <span className="text-white/40">•</span>
            <span className="text-white/90 text-[11px] font-medium">Real-Time Graph Causal AI</span>
          </motion.div>

          {/* Headline in Crisp Pure White */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
            className="text-center font-bold text-4xl sm:text-5xl md:text-6xl lg:text-[68px] leading-[1.08] tracking-[-0.03em] text-white max-w-4xl mt-0 mb-6 drop-shadow-[0_4px_24px_rgba(0,0,0,0.9)]"
          >
            Predict Failure Blast Radius <br />
            <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent italic font-serif drop-shadow-[0_4px_24px_rgba(0,0,0,0.8)]">
              Before Outages Happen
            </span>
          </motion.h1>

          {/* Subheadline in Clear White */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
            className="text-center text-sm md:text-base text-white/95 max-w-2xl leading-relaxed mb-8 drop-shadow-[0_2px_12px_rgba(0,0,0,0.85)] font-normal"
          >
            Transform reactive firefighting into proactive SRE resilience. Real-time telemetry ingestion,
            dependency graph traversal, and supervised automated runbooks to keep your services at 99.99% uptime.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3, ease: 'easeOut' }}
            className="flex flex-col sm:flex-row items-center gap-3.5"
          >
            <button
              onClick={handleAction}
              className="rounded-full px-8 py-3.5 text-sm font-bold bg-gradient-to-r from-indigo-500 to-cyan-500 text-white hover:brightness-110 transition-all shadow-2xl hover:scale-105 active:scale-95 flex items-center gap-2 border border-white/20"
              style={{ boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.4)' }}
            >
              <span>Launch Operations Console</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <a
              href="#how-it-works"
              className="rounded-full px-6 py-3.5 text-sm font-semibold bg-white/15 backdrop-blur-xl border border-white/25 text-white hover:bg-white/25 transition-all flex items-center gap-2 hover:scale-105 shadow-lg"
            >
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Explore Architecture</span>
            </a>
          </motion.div>

          <span className="mt-4 text-xs text-white/80 font-mono drop-shadow-[0_1px_6px_rgba(0,0,0,0.8)]">
            Zero Agent Footprint • Live SSE Stream • Enterprise RBAC
          </span>

          {/* Stack Logos Row with High-Contrast Glass Chips */}
          <motion.div
            variants={{
              hidden: { opacity: 0 },
              show: {
                opacity: 1,
                transition: {
                  staggerChildren: 0.08,
                  delayChildren: 0.4,
                },
              },
            }}
            initial="hidden"
            animate="show"
            className="mt-14 flex flex-wrap justify-center items-center gap-3 md:gap-4 max-w-3xl"
          >
            {stackLogos.map((tech) => (
              <motion.div
                key={tech.name}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  show: { opacity: 1, y: 0 },
                }}
                whileHover={{ scale: 1.05 }}
                className="px-3.5 py-1.5 rounded-full bg-black/50 backdrop-blur-md border border-white/20 text-white/90 text-xs font-mono font-medium hover:border-cyan-400/60 hover:text-white transition-all shadow-md"
              >
                {tech.label}
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
