import React, { useEffect, useRef } from 'react';
import { useInView } from 'framer-motion';
import ScrollExpand from '../components/ScrollExpand';

// Counter component for stats with smooth animation
function CountUp({ end }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    let current = 0;
    const duration = 1200; // ms
    const frameRate = 1000 / 60;
    const totalFrames = Math.round(duration / frameRate);
    const increment = end / totalFrames;
    let frame = 0;

    const interval = setInterval(() => {
      frame++;
      current += increment;
      if (frame >= totalFrames || current >= end) {
        if (ref.current) ref.current.textContent = end;
        clearInterval(interval);
      } else {
        if (ref.current) ref.current.textContent = Math.floor(current);
      }
    }, frameRate);

    return () => clearInterval(interval);
  }, [end]);

  return <span ref={ref}>0</span>;
}

export function HeroSection({ onLaunchApp }) {
  return (
    <div className="relative">
      {/* Top Navigation Bar */}
      <nav className="absolute top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-6 backdrop-blur-md bg-black/40 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-black text-black text-lg shadow-lg shadow-cyan-500/30">
            S
          </div>
          <span className="font-extrabold text-xl tracking-wider text-white">
            SYNAPSE <span className="text-cyan-400 font-normal">RISKOPS</span>
          </span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-neutral-300">
          <a href="#problem" className="hover:text-cyan-400 transition-colors">The Problem</a>
          <a href="#how-it-works" className="hover:text-cyan-400 transition-colors">How It Works</a>
          <a href="#capabilities" className="hover:text-cyan-400 transition-colors">Capabilities</a>
          <a href="#tech-stack" className="hover:text-cyan-400 transition-colors">Tech Stack</a>
        </div>
        <button
          onClick={onLaunchApp}
          className="px-5 py-2.5 rounded-lg text-xs tracking-wider uppercase font-bold bg-cyan-400 text-black hover:bg-cyan-300 shadow-md shadow-cyan-400/20 transition-all hover:scale-105 active:scale-95"
        >
          Launch Console
        </button>
      </nav>

      {/* Hero with ScrollExpand Component */}
      <ScrollExpand
        src="/gemini_generated_video_a62a1b95.mp4"
        mediaType="video"
        alt="Synapse RiskOps cinematic demo"
        title="Synapse RiskOps"
        scrollHint="Scroll to expand"
        startWidth={42}
        startHeight={58}
        startRadius={24}
        endRadius={0}
        mediaZoom={1.3}
        scrollDistance={1.4}
        holdDistance={0.6}
        smoothing={0.1}
        overlayScrim={0.65}
        useWindowScroll={true}
        enabled={true}
        className="hero-section"
      >
        <div className="scroll-expand__overlay-content">
          <h2 className="overlay-subheading">Autonomous Risk Operations Platform</h2>
          <p className="overlay-tagline">
            Predict infrastructure failures. Diagnose root causes. Automate recovery.
          </p>
          <div className="flex justify-center gap-4 mt-2">
            <button
              onClick={onLaunchApp}
              className="btn btn-primary text-sm uppercase tracking-wider font-bold py-2.5 px-6"
            >
              Open Live Console
            </button>
          </div>
          <p className="overlay-credit">Built by a team of AI/ML engineers</p>
        </div>
      </ScrollExpand>
    </div>
  );
}

export function ProblemSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  const stats = [
    { value: 3.2, isFloat: true, label: 'hours', desc: 'Average MTTR' },
    { value: 60, isFloat: false, label: '%', desc: 'False positive rate' },
    { value: 847, isFloat: false, label: 'alerts/wk', desc: 'Per on-call engineer' },
    { value: null, textValue: 'Manual', label: 'RCA', desc: 'Hours to days' },
  ];

  return (
    <section id="problem" ref={ref} className="problem-section">
      <div className="problem-container">
        <div className="stats-grid">
          {stats.map((stat, i) => (
            <div key={i} className="stat-card group">
              <div className="stat-value">
                {stat.textValue ? (
                  stat.textValue
                ) : (
                  <>
                    {isInView ? <CountUp end={stat.value} /> : '0'}
                    {stat.isFloat ? '.2' : ''}
                  </>
                )}
                <span className="text-sm font-medium text-neutral-400 ml-1.5 uppercase tracking-wide">
                  {stat.label}
                </span>
              </div>
              <p className="stat-desc">{stat.desc}</p>
            </div>
          ))}
        </div>
        <div className="problem-copy">
          <div className="inline-block px-3 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 font-mono text-xs uppercase tracking-wider mb-4">
            Systemic Fatigue
          </div>
          <h2>The Problem</h2>
          <p>
            Alert fatigue is killing your team. Manual root cause analysis delays mitigation.
            Your incidents are preventable — but only if you catch them early.
          </p>
          <div className="mt-8 pt-6 border-t border-neutral-800/80 flex items-center gap-6 text-sm text-neutral-400">
            <div>
              <span className="text-white font-bold block text-lg">73%</span>
              <span>Downtime caused by delayed RCA</span>
            </div>
            <div className="w-px h-8 bg-neutral-800" />
            <div>
              <span className="text-white font-bold block text-lg">$300K+</span>
              <span>Cost per hour of enterprise outage</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="how-it-works-section">
      <div className="max-w-4xl mx-auto text-center mb-6">
        <div className="inline-block px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-3">
          Architecture & Flow
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">How It Works</h2>
      </div>

      <div className="architecture-diagram">
        <svg viewBox="0 0 840 260" className="arch-svg w-full h-auto">
          <defs>
            <linearGradient id="cyberGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00d9ff" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.15" />
            </linearGradient>
            <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Grid lines in background */}
          <line x1="0" y1="130" x2="840" y2="130" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />

          {/* Input layer */}
          <g className="layer input-layer">
            <rect x="30" y="70" width="200" height="120" rx="12" fill="url(#cyberGrad)" stroke="#38bdf8" strokeWidth="1.5" />
            <text x="130" y="115" textAnchor="middle" fill="#ffffff" fontWeight="700" fontSize="16">Logs & Metrics</text>
            <text x="130" y="140" textAnchor="middle" fill="#94a3b8" fontSize="12">OTel • Prometheus • Logs</text>
            <circle cx="130" cy="165" r="4" fill="#38bdf8" filter="url(#neonGlow)" />
          </g>

          {/* Processing layer */}
          <g className="layer ml-layer">
            <rect x="320" y="55" width="200" height="150" rx="12" fill="url(#cyberGrad)" stroke="#818cf8" strokeWidth="1.5" />
            <text x="420" y="105" textAnchor="middle" fill="#ffffff" fontWeight="700" fontSize="17">ML Engine</text>
            <text x="420" y="130" textAnchor="middle" fill="#a5b4fc" fontSize="12">Prophet Forecasting</text>
            <text x="420" y="150" textAnchor="middle" fill="#a5b4fc" fontSize="12">Isolation Forest RCA</text>
            <text x="420" y="170" textAnchor="middle" fill="#a5b4fc" fontSize="12">NetworkX Blast Radius</text>
          </g>

          {/* Output layer */}
          <g className="layer output-layer">
            <rect x="610" y="70" width="200" height="120" rx="12" fill="url(#cyberGrad)" stroke="#34d399" strokeWidth="1.5" />
            <text x="710" y="115" textAnchor="middle" fill="#ffffff" fontWeight="700" fontSize="16">Resolution</text>
            <text x="710" y="140" textAnchor="middle" fill="#94a3b8" fontSize="12">LangGraph • n8n Playbooks</text>
            <circle cx="710" cy="165" r="4" fill="#34d399" filter="url(#neonGlow)" />
          </g>

          {/* Connecting arrows with animation */}
          <line x1="230" y1="130" x2="320" y2="130" className="flow-line" stroke="#38bdf8" />
          <polygon points="315,126 324,130 315,134" fill="#38bdf8" />

          <line x1="520" y1="130" x2="610" y2="130" className="flow-line" stroke="#34d399" />
          <polygon points="605,126 614,130 605,134" fill="#34d399" />
        </svg>
      </div>

      <p className="supporting-copy mt-8">
        Every component of Synapse is built to answer one question:{' '}
        <strong className="text-cyan-300 font-semibold">why did my infrastructure fail, and what do I do now?</strong>
      </p>
    </section>
  );
}

export function CapabilitiesSection() {
  const capabilities = [
    {
      icon: '⚡',
      title: 'Anomaly Detection',
      desc: 'Real-time scoring with Isolation Forest across high-frequency metric streams.',
    },
    {
      icon: '🔮',
      title: 'Failure Prediction',
      desc: 'Prophet forecasting predicts impact windows 6+ hours before user degradation.',
    },
    {
      icon: '🗺️',
      title: 'Dependency Mapping',
      desc: 'NetworkX graph modeling visualizes blast radius and topological failure cascades.',
    },
    {
      icon: '📊',
      title: 'Risk Scoring',
      desc: 'Composite multi-dimensional scores guide urgent triage and on-call routing.',
    },
    {
      icon: '🤖',
      title: 'Autonomous Routing',
      desc: 'LangGraph multi-agent pipeline routes to auto-remediation playbooks or escalates.',
    },
    {
      icon: '🔄',
      title: 'Self-Improving',
      desc: 'Incident feedback loop refines predictions and weights heuristics over time.',
    },
  ];

  return (
    <section id="capabilities" className="capabilities-section">
      <div className="max-w-4xl mx-auto text-center">
        <div className="inline-block px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-3">
          Deep Tech Stack
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Key Capabilities</h2>
      </div>

      <div className="capabilities-grid">
        {capabilities.map((cap, i) => (
          <div key={i} className="capability-card group">
            <div className="cap-icon group-hover:scale-110 transition-transform duration-300">
              {cap.icon}
            </div>
            <h3>{cap.title}</h3>
            <p>{cap.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function TechStackSection() {
  const stack = {
    'Frontend': ['React', 'Vite', 'Tailwind', 'ReactFlow', 'Recharts'],
    'Backend': ['Spring Boot 3.3', 'Spring Security', 'JWT', 'AsyncPG'],
    'ML Engine': ['FastAPI', 'Scikit-learn', 'Prophet', 'NetworkX'],
    'Automation': ['n8n', 'LangGraph', 'Gemini API', 'Ansible AWX'],
    'Database & Storage': ['PostgreSQL', 'TimescaleDB', 'Redis'],
    'Deployment': ['Docker', 'Docker Compose', 'Kubernetes', 'OpenTelemetry'],
  };

  return (
    <section id="tech-stack" className="tech-stack-section">
      <div className="max-w-4xl mx-auto text-center mb-6">
        <div className="inline-block px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-3">
          Architecture
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Enterprise-grade Tools</h2>
        <p className="text-neutral-400 mt-2">Built with production-scale technologies</p>
      </div>

      <div className="tech-grid">
        {Object.entries(stack).map(([category, techs]) => (
          <div key={category} className="tech-category hover:border-cyan-500/50 transition-colors">
            <h4>{category}</h4>
            <div className="tech-badges">
              {techs.map(tech => (
                <span key={tech} className="tech-badge">{tech}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function CTASection({ onLaunchApp }) {
  return (
    <section className="cta-section">
      <div className="cta-container">
        <div className="cta-copy">
          <div className="inline-block px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-4">
            Get Started Now
          </div>
          <h2>Ready to eliminate MTTR?</h2>
          <p>Start with sample telemetry data or connect your own infrastructure logs in minutes.</p>
          <ul className="cta-checklist">
            <li>
              <span className="text-cyan-400 font-bold">✓</span> No credit card required
            </li>
            <li>
              <span className="text-cyan-400 font-bold">✓</span> Full access to autonomous incident workflows
            </li>
            <li>
              <span className="text-cyan-400 font-bold">✓</span> Onboarding walkthrough & sample data included
            </li>
          </ul>
          <div className="cta-buttons">
            <button onClick={onLaunchApp} className="btn btn-primary">
              Start Free Trial
            </button>
            <button onClick={onLaunchApp} className="btn btn-secondary">
              Open Dashboard
            </button>
          </div>
        </div>

        {/* Visual card mimicking interactive ops monitor */}
        <div className="relative p-6 rounded-2xl bg-neutral-900/90 border border-cyan-500/30 shadow-2xl shadow-cyan-500/10">
          <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
              <span className="font-mono text-xs text-neutral-300">INCIDENT-4091: REDIS_MEMORY_SPIKE</span>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
              CRITICAL
            </span>
          </div>
          <div className="py-4 space-y-3 font-mono text-xs">
            <div className="text-neutral-400">
              <span className="text-cyan-400">root_cause_analysis:</span> Cluster node 4 memory leak in query cache
            </div>
            <div className="text-neutral-400">
              <span className="text-cyan-400">prophet_forecast:</span> Out of memory predicted in <span className="text-amber-400">22 minutes</span>
            </div>
            <div className="text-neutral-400">
              <span className="text-cyan-400">autonomous_action:</span> LangGraph agent triggered flush_evict playbook
            </div>
          </div>
          <div className="pt-4 border-t border-neutral-800 flex justify-between items-center text-xs">
            <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
              ● Automated Mitigation Active
            </span>
            <button onClick={onLaunchApp} className="text-cyan-400 hover:underline">
              Inspect Graph →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function LandingPage({ onLaunchApp }) {
  return (
    <div className="w-full min-h-screen bg-black text-slate-100 selection:bg-cyan-500 selection:text-black">
      <HeroSection onLaunchApp={onLaunchApp} />
      <ProblemSection />
      <HowItWorksSection />
      <CapabilitiesSection />
      <TechStackSection />
      <CTASection onLaunchApp={onLaunchApp} />

      {/* Footer */}
      <footer className="py-12 border-t border-neutral-900 bg-black text-center text-neutral-500 text-sm">
        <p>© 2026 Synapse RiskOps. Autonomous Risk Operations & AIOps Platform.</p>
      </footer>
    </div>
  );
}
