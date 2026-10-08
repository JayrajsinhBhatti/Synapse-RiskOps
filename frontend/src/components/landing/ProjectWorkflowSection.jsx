/**
 * frontend/src/components/landing/ProjectWorkflowSection.jsx
 * 
 * Complete End-to-End System Workflow of Synapse RiskOps.
 * Placed immediately before the "Core AI & Orchestration Engine / Explore the Power of Synapse RiskOps AI" section.
 * 
 * Features:
 * 1. Interactive 6-Stage Lifecycle Pipeline:
 *    - Phase 1: Real-Time Telemetry Harvesting & Stream Ingestion (Prometheus & Bridge)
 *    - Phase 2: ML Anomaly Inference & Predictive Risk Scoring (IsolationForest)
 *    - Phase 3: Topology Blast Radius & GenAI Root-Cause Diagnosis (DAG & Gemini)
 *    - Phase 4: Dual-Confidence Decision & Safety Routing Gateway (Confidence Router)
 *    - Phase 5: Automated Infrastructure Remediation (Ansible Semaphore & Docker)
 *    - Phase 6: Closed-Loop Verification & Immutable Audit Trail (PostgreSQL & SSE)
 * 2. Interactive Step Switcher with active progress bar and auto-cycle toggle.
 * 3. Live Interactive Terminal / Telemetry Preview for every stage.
 * 4. Architectural Dataflow Architecture diagram toggle.
 * 5. Full dark mode / light mode theme support with Chakra Petch typography.
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Cpu,
  Network,
  ShieldCheck,
  ShieldAlert,
  Terminal,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Server,
  Database,
  Radio,
  Play,
  Pause,
  ExternalLink,
  Layers,
  Zap,
  GitBranch,
  RefreshCw,
  Clock,
  ChevronRight,
  Sliders,
  Check,
} from 'lucide-react';

const WORKFLOW_STAGES = [
  {
    id: 1,
    phase: 'Stage 01',
    title: 'Telemetry Harvesting & Stream Ingestion',
    shortTitle: 'Telemetry Harvesting',
    tag: 'Prometheus & Bridge :9010',
    icon: Activity,
    color: 'cyan',
    badgeClass: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    description:
      'Continuous telemetry collection from 6 microservices (api-gateway, auth, order, payment, inventory, notification). Prometheus scrapes golden signals every 1.5s, buffered through the high-throughput Telemetry Bridge.',
    technologies: ['Prometheus :9090', 'Telemetry Bridge :9010', 'Docker cAdvisor', 'OpenTelemetry'],
    inputs: 'Live HTTP metrics, CPU/Mem usage, latency percentiles, error logs',
    outputs: 'Normalized 8-dimensional telemetry vectors ready for ML inference',
    previewType: 'telemetry',
    metrics: [
      { label: 'Ingestion Stream', value: '1.5s Tick Interval', highlight: true },
      { label: 'Active Targets', value: '6 Microservices', highlight: false },
      { label: 'Scraped Metrics', value: 'P99, 5xx%, CPU, RAM, Conns', highlight: false },
      { label: 'Telemetry Queue', value: 'Sub-millisecond Latency', highlight: true },
    ],
    consoleLogs: [
      '[PROMETHEUS] Scraping target: http://payment-service:8003/metrics [200 OK]',
      '[TELEMETRY-BRIDGE] Ingested 1,420 metric points/sec from cluster network',
      '[SIGNALS] payment-service: P99=480ms (ANOMALY), CPU=88.4%, 5xx=4.8%',
      '[BRIDGE] Serializing vector and routing to ML Risk Engine (:8000)...',
    ],
  },
  {
    id: 2,
    phase: 'Stage 02',
    title: 'ML Anomaly Inference & Early Risk Scoring',
    shortTitle: 'Predictive ML Engine',
    tag: 'Isolation Forest + Time-Series',
    icon: Cpu,
    color: 'indigo',
    badgeClass: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
    description:
      'Multi-variate anomaly engine analyzes incoming telemetry vectors against dynamic baselines. Calculates composite Risk Scores (0-100) and predicts impending failures up to 15 minutes before user SLA degradation.',
    technologies: ['FastAPI ML Engine :8000', 'Isolation Forest v1', 'Statsmodels', 'NumPy / Scikit-Learn'],
    inputs: 'Multi-dimensional telemetry metrics from Bridge',
    outputs: 'Composite Risk Score (0-100), Risk Tier (HEALTHY / ELEVATED / CRITICAL), Failure Type',
    previewType: 'ml',
    metrics: [
      { label: 'Risk Score', value: '84.2 / 100', highlight: true },
      { label: 'Current Tier', value: 'CRITICAL', highlight: true },
      { label: 'Predicted Failure', value: 'HIGH_TRAFFIC_CONGESTION', highlight: false },
      { label: 'Lead Time', value: '15 min Horizon Warning', highlight: false },
    ],
    consoleLogs: [
      '[ML ENGINE] Evaluated feature vector: [cpu=88.4, mem=76.2, p99=480, 5xx=4.8]',
      '[ISOLATION-FOREST] Anomaly score: -0.684 (Severe Outlier detected)',
      '[RISK ENGINE] Composite score escalated: 32 (HEALTHY) -> 84 (CRITICAL)',
      '[PREDICTION] Impending service starvation predicted within 12 minutes.',
    ],
  },
  {
    id: 3,
    phase: 'Stage 03',
    title: 'Topology Blast Radius & GenAI Root Cause (RCA)',
    shortTitle: 'Blast Radius & RCA',
    tag: 'NetworkX DAG + Gemini 2.0',
    icon: Network,
    color: 'rose',
    badgeClass: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    description:
      'Directed Acyclic Graph (DAG) traversal isolates the root-cause service from cascading victim services. Google Gemini agent inspects logs, topology edges, and telemetry anomalies to generate human-grade causal explanations.',
    technologies: ['NetworkX DAG Traversal', 'Google Gemini AI', 'Causal Bayesian Graph', 'Blast Radius Analyzer'],
    inputs: 'Microservice dependency graph & anomaly signatures',
    outputs: 'Root Cause Service identification, propagation blast radius, AI reasoning diagnosis',
    previewType: 'graph',
    metrics: [
      { label: 'Culprit Service', value: 'payment-service', highlight: true },
      { label: 'Blast Radius', value: '3 Downstream Nodes Affected', highlight: true },
      { label: 'Causal Chain', value: 'Gateway -> Order -> Payment', highlight: false },
      { label: 'RCA Confidence', value: '92.4% Certainty', highlight: false },
    ],
    consoleLogs: [
      '[GRAPH-TRAVERSAL] Breadth-first scan across 6 dependency nodes...',
      '[BLAST RADIUS] Victim services: [order-service, notification-service]',
      '[RCA ISOLATION] Root cause culprit isolated: payment-service (Central Bottleneck)',
      '[GEMINI RCA] "Worker thread pool exhaustion causing cascading backpressure upstream."',
    ],
  },
  {
    id: 4,
    phase: 'Stage 04',
    title: 'Dual-Confidence Decision & Safety Routing Gateway',
    shortTitle: 'Confidence Routing',
    tag: 'Confidence Router & SRE Guardrails',
    icon: Sliders,
    color: 'amber',
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    description:
      'Rigorous decision gateway compares ML confidence (ML_conf >= 0.85) and RCA confidence (RCA_conf >= 0.80). Routes to autonomous execution for high-certainty events or gates with one-click human approval for safety-critical actions.',
    technologies: ['Person 1 Confidence Router', 'RBAC Security Matrix', 'Safety Guardrails', 'Orchestration Rules'],
    inputs: 'ML confidence score, RCA certainty, service tier criticality',
    outputs: 'Routing decision (auto_remediate vs escalate) & recommended Ansible runbook',
    previewType: 'router',
    metrics: [
      { label: 'ML Confidence', value: '91.0% (Threshold: >= 85%)', highlight: true },
      { label: 'RCA Confidence', value: '88.5% (Threshold: >= 80%)', highlight: true },
      { label: 'Routing Decision', value: 'AUTO_REMEDIATE', highlight: true },
      { label: 'Runbook Selected', value: 'SCALE_OUT_PODS / REPLICAS', highlight: false },
    ],
    consoleLogs: [
      '[CONFIDENCE-ROUTER] Evaluating safety matrix: ML=0.910, RCA=0.885',
      '[POLICY-CHECK] Both thresholds satisfied for automated remediation criteria.',
      '[SAFETY-GUARDRAIL] Verified target service state: Safe for zero-downtime scaling.',
      '[DISPATCH-TRIGGER] Approved for execution: Disagreeing threshold escalation BYPASSED.',
    ],
  },
  {
    id: 5,
    phase: 'Stage 05',
    title: 'Automated Infrastructure Remediation via Ansible',
    shortTitle: 'Ansible Semaphore',
    tag: 'Semaphore :3000 & Docker Engine',
    icon: Terminal,
    color: 'emerald',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    description:
      'Triggers real Ansible playbooks via Semaphore REST API (http://localhost:3000/project/1/history). Automatically restarts failing pods, scales memory/replicas, prunes disk storage, or resets network routes with play-by-play audit logs.',
    technologies: ['Ansible Semaphore :3000', 'Docker Engine API', 'YAML Playbooks', 'n8n & Activepieces'],
    inputs: 'Remediation task payload (target service, runbook ID, environment params)',
    outputs: 'Ansible Semaphore Task execution with stdout logs, exit codes, and timing',
    previewType: 'ansible',
    metrics: [
      { label: 'Execution Engine', value: 'Ansible Semaphore :3000', highlight: true },
      { label: 'Dispatched Task', value: 'Task #244 (Project 1)', highlight: true },
      { label: 'Playbook', value: 'scale_resources.yml', highlight: false },
      { label: 'Execution Time', value: '3.42 seconds', highlight: false },
    ],
    consoleLogs: [
      '[SEMAPHORE-API] POST /api/project/1/tasks -> Created Task #244 (scale_resources.yml)',
      '[ANSIBLE] TASK [Update container memory allocation via Docker update] => ok',
      '[ANSIBLE] TASK [Post-remediation validation: verify new memory limit] => ok',
      '[ANSIBLE] Container payment-service scaled with memory limit 2g. Host status: SUCCESS',
    ],
  },
  {
    id: 6,
    phase: 'Stage 06',
    title: 'Closed-Loop Verification & Immutable Audit Trail',
    shortTitle: 'Recovery Verification',
    tag: 'PostgreSQL 16 & Live SSE Streams',
    icon: ShieldCheck,
    color: 'purple',
    badgeClass: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    description:
      'Automated synthetic health probe (/healthz) verifies latency restoration (<350ms) and zero error rate. Persists immutable audit trail with Semaphore Task ID to PostgreSQL 16 and streams live updates across dashboards via Server-Sent Events.',
    technologies: ['PostgreSQL 16 Audit Store', 'FastAPI SSE Manager', 'Synthetic Health Probe', 'React SSE Stream'],
    inputs: 'Post-remediation container telemetry & health response probes',
    outputs: 'Mathematical recovery proof, PostgreSQL audit history record, real-time UI refresh',
    previewType: 'verify',
    metrics: [
      { label: 'Health Probe', value: '200 OK (/healthz)', highlight: true },
      { label: 'P99 Recovery', value: '480ms -> 42ms (-91.2%)', highlight: true },
      { label: 'Risk Normalized', value: '84 (CRIT) -> 28 (HEALTHY)', highlight: true },
      { label: 'Audit Trail', value: 'Committed to PostgreSQL', highlight: false },
    ],
    consoleLogs: [
      '[HEALTH-PROBE] GET http://payment-service:8003/healthz -> 200 OK (Latency: 42ms)',
      '[METRIC-VALIDATION] 5xx error rate normalized to 0.00% (SLA Restored)',
      '[POSTGRESQL] Incident #fd7d53e5 status updated: RESOLVED. Task #244 linked.',
      '[SSE-BROADCAST] Event "incident_resolved" pushed to active dashboard clients.',
    ],
  },
];

export default function ProjectWorkflowSection({ onGetStarted, className }) {
  const [activeStep, setActiveStep] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  // Auto-cycle through the stages every 6.5 seconds when active
  useEffect(() => {
    if (!isAutoPlaying) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % WORKFLOW_STAGES.length);
    }, 6500);
    return () => clearInterval(interval);
  }, [isAutoPlaying]);

  const currentStage = WORKFLOW_STAGES[activeStep];
  const CurrentIcon = currentStage.icon;

  return (
    <section
      id="workflow"
      className={
        'w-full px-4 sm:px-6 md:px-12 lg:px-20 py-24 dark:bg-slate-950 bg-slate-50 relative overflow-hidden transition-colors duration-300 border-b dark:border-white/5 border-slate-200/80 ' +
        (className || '')
      }
    >
      {/* Background Ambience Glows */}
      <div className="absolute top-1/4 -left-48 w-96 h-96 bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-indigo-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        {/* =========================================================================
            SECTION HEADER
           ========================================================================= */}
        <div className="text-center max-w-3xl mx-auto mb-14 space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-600 dark:text-cyan-400 text-xs font-mono font-semibold"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>End-to-End System Operational Pipeline</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-3xl md:text-5xl font-black dark:text-white text-slate-900 tracking-tight leading-[1.15]"
            style={{ fontFamily: "'Chakra Petch', sans-serif" }}
          >
            How Synapse RiskOps Works <br />
            <span className="bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
              From Telemetry Anomaly to Automated Remediation
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="text-sm md:text-base text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed"
          >
            A multi-agent, closed-loop reliability ecosystem. Follow how real-time microservice signals flow
            through the ML risk engine, graph RCA, confidence routing, and Ansible Semaphore playbooks.
          </motion.p>
        </div>

        {/* =========================================================================
            STAGE SELECTOR / PROGRESS TABS
           ========================================================================= */}
        <div className="mb-10">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3">
            {WORKFLOW_STAGES.map((stage, idx) => {
              const Icon = stage.icon;
              const isActive = activeStep === idx;
              return (
                <button
                  key={stage.id}
                  onClick={() => {
                    setActiveStep(idx);
                    setIsAutoPlaying(false);
                  }}
                  className={`relative p-3.5 rounded-2xl text-left transition-all duration-300 flex flex-col justify-between border ${
                    isActive
                      ? 'dark:bg-slate-900/90 bg-white dark:border-cyan-500/50 border-cyan-500/60 shadow-lg dark:shadow-cyan-950/40 shadow-cyan-100'
                      : 'dark:bg-slate-900/40 bg-white/70 dark:border-white/5 border-slate-200/80 dark:hover:bg-slate-900/70 hover:bg-white'
                  }`}
                >
                  {/* Top indicator bar */}
                  {isActive && (
                    <motion.div
                      layoutId="activeTabGlow"
                      className="absolute inset-x-3 -top-px h-1 rounded-full bg-gradient-to-r from-cyan-400 to-indigo-500"
                    />
                  )}

                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                        isActive
                          ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400'
                          : 'dark:bg-slate-800 bg-slate-100 text-slate-500'
                      }`}
                    >
                      {stage.phase}
                    </span>
                    <Icon
                      className={`w-4 h-4 ${
                        isActive ? 'text-cyan-500 dark:text-cyan-400' : 'text-slate-400'
                      }`}
                    />
                  </div>

                  <span
                    className={`text-xs font-bold leading-snug line-clamp-2 ${
                      isActive ? 'dark:text-white text-slate-900' : 'dark:text-slate-400 text-slate-600'
                    }`}
                  >
                    {stage.shortTitle}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Autoplay / Manual Controls Toggle */}
          <div className="flex items-center justify-between mt-3 px-2 text-xs text-slate-500 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              Active Phase: {currentStage.phase} of 06
            </span>
            <button
              onClick={() => setIsAutoPlaying(!isAutoPlaying)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg dark:bg-slate-900 bg-slate-200/80 dark:hover:bg-slate-800 hover:bg-slate-300 dark:text-slate-300 text-slate-700 transition-colors"
            >
              {isAutoPlaying ? (
                <>
                  <Pause className="w-3 h-3 text-cyan-400" /> Auto-cycling (6.5s)
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 text-emerald-400" /> Resume Auto-cycle
                </>
              )}
            </button>
          </div>
        </div>

        {/* =========================================================================
            ACTIVE STAGE DEEP DIVE (SPLIT DISPLAY)
           ========================================================================= */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Left Column: Stage Explanation & Specs */}
          <div className="lg:col-span-6 flex flex-col justify-between p-6 sm:p-8 rounded-3xl dark:bg-slate-900/80 bg-white border dark:border-white/10 border-slate-200/90 shadow-xl dark:shadow-black/30 space-y-6">
            <div className="space-y-4">
              {/* Badge & Title */}
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`text-xs font-mono font-bold px-3 py-1 rounded-full border ${currentStage.badgeClass}`}
                >
                  {currentStage.phase} • {currentStage.tag}
                </span>
              </div>

              <h3
                className="text-2xl sm:text-3xl font-extrabold dark:text-white text-slate-900 leading-tight"
                style={{ fontFamily: "'Chakra Petch', sans-serif" }}
              >
                {currentStage.title}
              </h3>

              <p className="text-sm dark:text-slate-300 text-slate-600 leading-relaxed">
                {currentStage.description}
              </p>
            </div>

            {/* Inputs & Outputs Specs */}
            <div className="space-y-3 pt-4 border-t dark:border-white/10 border-slate-200/80 text-xs font-mono">
              <div className="flex items-start gap-2">
                <span className="text-cyan-500 font-bold shrink-0">DATA IN &gt;</span>
                <span className="dark:text-slate-300 text-slate-700">{currentStage.inputs}</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold shrink-0">DATA OUT &gt;</span>
                <span className="dark:text-slate-300 text-slate-700">{currentStage.outputs}</span>
              </div>
            </div>

            {/* Technology Chips */}
            <div className="pt-4 border-t dark:border-white/10 border-slate-200/80">
              <span className="text-[11px] font-mono text-slate-400 block mb-2 uppercase tracking-wider">
                Integrated Core Technologies
              </span>
              <div className="flex flex-wrap gap-1.5">
                {currentStage.technologies.map((tech, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 rounded-lg dark:bg-slate-950 bg-slate-100 dark:text-slate-300 text-slate-700 border dark:border-white/5 border-slate-200 text-xs font-mono"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>

            {/* Next Step Nav Bar */}
            <div className="pt-4 flex items-center justify-between border-t dark:border-white/10 border-slate-200/80 text-xs">
              <span className="text-slate-400 font-mono">
                Pipeline Progression: Step {activeStep + 1} of {WORKFLOW_STAGES.length}
              </span>
              <button
                onClick={() => {
                  setActiveStep((prev) => (prev + 1) % WORKFLOW_STAGES.length);
                  setIsAutoPlaying(false);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold dark:bg-cyan-500/10 bg-cyan-50 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 transition-all"
              >
                Next Stage <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Right Column: Live Interactive Telemetry Console / Visual Artifacts */}
          <div className="lg:col-span-6 flex flex-col justify-between p-6 sm:p-8 rounded-3xl dark:bg-slate-950 bg-slate-900 border border-slate-800 shadow-2xl text-white space-y-6">
            {/* Top Bar with Live Indicator */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono font-bold text-slate-300">
                  Execution Artifact & Console
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-mono text-emerald-400">ACTIVE TELEMETRY</span>
              </div>
            </div>

            {/* Stage KPI Metric Highlights */}
            <div className="grid grid-cols-2 gap-3">
              {currentStage.metrics.map((m, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-xl border ${
                    m.highlight
                      ? 'bg-slate-900/90 border-cyan-500/40 text-cyan-300'
                      : 'bg-slate-900/50 border-slate-800 text-slate-300'
                  }`}
                >
                  <span className="text-[10px] font-mono text-slate-400 block truncate">
                    {m.label}
                  </span>
                  <span className="text-sm font-mono font-bold block mt-0.5 truncate">
                    {m.value}
                  </span>
                </div>
              ))}
            </div>

            {/* Live Terminal Output Feed */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>Console Log Trace</span>
                <span className="text-[10px] text-slate-500">Live Daemon Feed</span>
              </div>
              <div className="bg-black/90 p-4 rounded-xl border border-slate-800 font-mono text-xs space-y-2 min-h-[140px] max-h-[160px] overflow-y-auto">
                {currentStage.consoleLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-cyan-500 shrink-0 select-none">&gt;</span>
                    <span
                      className={
                        log.includes('CRITICAL') || log.includes('ANOMALY')
                          ? 'text-rose-400 font-bold'
                          : log.includes('SUCCESS') || log.includes('RESOLVED') || log.includes('200 OK')
                          ? 'text-emerald-400 font-semibold'
                          : 'text-slate-300'
                      }
                    >
                      {log}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Direct Verification Badge */}
            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-slate-300 font-mono text-[11px]">
                  {activeStep === 4
                    ? 'Ansible Semaphore: http://localhost:3000/project/1/history'
                    : 'Real-time sync to PostgreSQL 16 & ML Risk Engine'}
                </span>
              </div>
              {onGetStarted && (
                <button
                  onClick={onGetStarted}
                  className="text-cyan-400 hover:text-cyan-300 hover:underline text-[11px] font-mono font-bold flex items-center gap-1"
                >
                  Explore Live <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* =========================================================================
            HORIZONTAL ARCHITECTURE FLOW DIAGRAM & ANSIBLE REMEDIATION LAYER
           ========================================================================= */}
        <div className="mt-14 p-6 sm:p-8 rounded-3xl dark:bg-slate-900/60 bg-white/80 border dark:border-white/10 border-slate-200/90 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b dark:border-white/10 border-slate-200/80 pb-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 mb-1">
                <span>HORIZONTAL ARCHITECTURE DATAFLOW</span>
              </div>
              <h4
                className="text-lg sm:text-xl font-bold dark:text-white text-slate-900 tracking-tight"
                style={{ fontFamily: "'Chakra Petch', sans-serif" }}
              >
                End-to-End System Architecture (8 Core Layers)
              </h4>
              <p className="text-xs text-slate-500">
                Data pipeline traverses horizontally from real microservices to automated Ansible remediation and closed-loop validation
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
                Scroll horizontally &gt;
              </span>
              <a
                href="http://localhost:3000/project/1/history"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-mono text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all shrink-0"
              >
                Ansible Semaphore History <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* 1. HORIZONTAL ONLY ARCHITECTURE PIPELINE */}
          <div className="overflow-x-auto pb-4 pt-2 -mx-2 px-2 scrollbar-thin scrollbar-thumb-slate-700/60 scrollbar-track-slate-900/30">
            <div className="flex items-stretch min-w-[1380px] gap-2 lg:gap-3">
              {[
                {
                  id: '01',
                  name: 'LIVE MICROSERVICES',
                  sub: 'Gateway, Auth, Order, Payment, Inventory...',
                  icon: Server,
                  color: 'cyan',
                  border: 'border-cyan-500/40',
                  badge: 'Microservices',
                  badgeColor: 'text-cyan-400 bg-cyan-500/10',
                },
                {
                  id: '02',
                  name: 'OBSERVABILITY LAYER',
                  sub: 'Prometheus + OpenTelemetry + Alertmanager',
                  icon: Radio,
                  color: 'indigo',
                  border: 'border-indigo-500/40',
                  badge: 'Prometheus :9090',
                  badgeColor: 'text-indigo-400 bg-indigo-500/10',
                },
                {
                  id: '03',
                  name: 'TELEMETRY BRIDGE',
                  sub: 'Converts live metrics → ML input',
                  icon: Activity,
                  color: 'blue',
                  border: 'border-blue-500/40',
                  badge: 'Bridge :9010',
                  badgeColor: 'text-blue-400 bg-blue-500/10',
                },
                {
                  id: '04',
                  name: 'INTELLIGENCE LAYER',
                  sub: 'ML + Statsmodels + NetworkX + LangGraph + Gemini',
                  icon: Cpu,
                  color: 'purple',
                  border: 'border-purple-500/40',
                  badge: 'RiskEngine :8000',
                  badgeColor: 'text-purple-400 bg-purple-500/10',
                },
                {
                  id: '05',
                  name: 'DECISION / ORCHESTRATION',
                  sub: 'FastAPI + Confidence Router + n8n',
                  icon: Sliders,
                  color: 'amber',
                  border: 'border-amber-500/40',
                  badge: 'FastAPI :8080',
                  badgeColor: 'text-amber-400 bg-amber-500/10',
                },
                {
                  id: '06',
                  name: 'REMEDIATION',
                  sub: 'Docker Runbooks + Ansible + Semaphore',
                  icon: Terminal,
                  color: 'emerald',
                  border: 'border-emerald-500/60 ring-2 ring-emerald-500/30',
                  badge: '⚡ Ansible :3000',
                  badgeColor: 'text-emerald-400 bg-emerald-500/20 font-bold',
                  isAnsible: true,
                },
                {
                  id: '07',
                  name: 'VERIFICATION',
                  sub: 'Prometheus + ML + Health Checks',
                  icon: CheckCircle2,
                  color: 'teal',
                  border: 'border-teal-500/40',
                  badge: 'Health Probe',
                  badgeColor: 'text-teal-400 bg-teal-500/10',
                },
                {
                  id: '08',
                  name: 'DATA + DASHBOARD',
                  sub: 'PostgreSQL + SSE + React Dashboard',
                  icon: Database,
                  color: 'rose',
                  border: 'border-rose-500/40',
                  badge: 'DB :5432 / :5173',
                  badgeColor: 'text-rose-400 bg-rose-500/10',
                },
              ].map((layer, idx, arr) => {
                const Icon = layer.icon;
                return (
                  <React.Fragment key={layer.id}>
                    <div
                      className={`flex-1 min-w-[155px] p-3.5 rounded-2xl border transition-all duration-300 flex flex-col justify-between ${
                        layer.isAnsible
                          ? 'dark:bg-emerald-950/30 bg-emerald-50/80 shadow-lg shadow-emerald-950/20 ' + layer.border
                          : 'dark:bg-slate-950/80 bg-white shadow-sm ' + layer.border
                      }`}
                    >
                      <div>
                        {/* Top Layer Header */}
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-mono font-bold text-slate-400">
                            LAYER {layer.id}
                          </span>
                          <span
                            className={`text-[9px] font-mono px-1.5 py-0.5 rounded-md ${layer.badgeColor}`}
                          >
                            {layer.badge}
                          </span>
                        </div>

                        {/* Icon & Title */}
                        <div className="flex items-center gap-2 mb-2">
                          <div
                            className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                              layer.isAnsible
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'dark:bg-slate-900 bg-slate-100 text-slate-300'
                            }`}
                          >
                            <Icon className="w-4 h-4" />
                          </div>
                          <h5
                            className="text-xs font-bold dark:text-white text-slate-900 leading-tight tracking-tight uppercase"
                            style={{ fontFamily: "'Chakra Petch', sans-serif" }}
                          >
                            {layer.name}
                          </h5>
                        </div>

                        {/* Description */}
                        <p className="text-[11px] dark:text-slate-400 text-slate-600 leading-snug">
                          {layer.sub}
                        </p>
                      </div>

                      {layer.isAnsible && (
                        <div className="mt-3 pt-2 border-t border-emerald-500/20 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          <span className="text-[10px] font-mono font-bold text-emerald-500 dark:text-emerald-400">
                            Automated Playbooks
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Horizontal Connector Arrow */}
                    {idx < arr.length - 1 && (
                      <div className="flex items-center justify-center text-slate-400 dark:text-slate-600 shrink-0 select-none">
                        <ArrowRight className="w-4 h-4" />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* 2. ANSIBLE REMEDIATION CAPABILITIES TABLE (LAYER 06 DEEP DIVE) */}
          <div className="p-5 sm:p-6 rounded-2xl dark:bg-slate-950 bg-slate-900 border border-emerald-500/30 text-white space-y-4 shadow-xl relative overflow-hidden">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider">
                      Layer 06 • Remediation Engine
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">
                      Ansible Semaphore :3000
                    </span>
                  </div>
                  <h5
                    className="text-sm font-bold text-white mt-0.5"
                    style={{ fontFamily: "'Chakra Petch', sans-serif" }}
                  >
                    Playbook Remediation Capabilities
                  </h5>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <span className="flex items-center gap-1 text-emerald-400">
                  <Check className="w-3.5 h-3.5" /> 5 Predefined Playbooks
                </span>
                <span className="text-slate-600">•</span>
                <span>Zero Downtime Execution</span>
              </div>
            </div>

            {/* Clean Markdown-Style Remediation Mapping Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] text-slate-400 uppercase tracking-wider bg-slate-900/60">
                    <th className="py-2.5 px-3 font-semibold">Problem</th>
                    <th className="py-2.5 px-3 font-semibold">Remediation Ansible can perform</th>
                    <th className="py-2.5 px-3 font-semibold">Target Playbook</th>
                    <th className="py-2.5 px-3 font-semibold">Action Mechanism</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  <tr className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-rose-300">
                      Service crashed
                    </td>
                    <td className="py-2.5 px-3 text-white font-medium">
                      🔄 Restart the Docker service
                    </td>
                    <td className="py-2.5 px-3 text-cyan-400">
                      restart_service.yml
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      docker restart synapse-&lt;service&gt; + inspect status
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-amber-300">
                      Memory/resource exhaustion
                    </td>
                    <td className="py-2.5 px-3 text-white font-medium">
                      📈 Increase resource allocation
                    </td>
                    <td className="py-2.5 px-3 text-cyan-400">
                      scale_resources.yml
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      docker update --memory 2g --memory-swap 2g
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-amber-300">
                      Disk/log bloat
                    </td>
                    <td className="py-2.5 px-3 text-white font-medium">
                      🧹 Clean unused Docker data/cache
                    </td>
                    <td className="py-2.5 px-3 text-cyan-400">
                      clear_disk.yml
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      docker image prune -f + system df reclaim
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-rose-300">
                      Network problem
                    </td>
                    <td className="py-2.5 px-3 text-white font-medium">
                      🌐 Reset the service's network connection
                    </td>
                    <td className="py-2.5 px-3 text-cyan-400">
                      reset_network.yml
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      docker network disconnect &amp; reconnect
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-indigo-300">
                      Other known problem
                    </td>
                    <td className="py-2.5 px-3 text-white font-medium">
                      🛠️ Run the corresponding predefined playbook
                    </td>
                    <td className="py-2.5 px-3 text-cyan-400">
                      custom_runbook.yml
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      POST /api/project/1/tasks with template extra_vars
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Bottom Info Bar */}
            <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t border-slate-800 text-[11px] font-mono text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Triggered automatically on high ML/RCA confidence or via one-click SRE approval in Synapse.
              </span>
              <a
                href="http://localhost:3000/project/1/history"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:text-cyan-300 hover:underline flex items-center gap-1 shrink-0"
              >
                Inspect Live Semaphore History &gt;
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
