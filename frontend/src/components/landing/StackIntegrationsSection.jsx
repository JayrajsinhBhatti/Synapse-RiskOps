/**
 * frontend/src/components/landing/StackIntegrationsSection.jsx
 * 
 * Auto-scrolling horizontal marquee of infrastructure & telemetry integrations.
 * Implements user's Integration01Kelo template with pause-on-hover and edge fading.
 */

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Server,
  Activity,
  Layers,
  Database,
  Terminal,
  Shield,
  Zap,
  Cpu,
  Radio,
  FileCode,
} from 'lucide-react';

const integrations = [
  {
    id: 'k8s',
    name: 'Kubernetes',
    category: 'Container Mesh',
    description: 'Auto-discovery of pods, replica sets, and deployment rollout health.',
    icon: <Server className="w-6 h-6 text-cyan-400" />,
  },
  {
    id: 'prometheus',
    name: 'Prometheus',
    category: 'Metrics Scrape',
    description: 'High-frequency PromQL telemetry pull for latency, memory, and CPU.',
    icon: <Activity className="w-6 h-6 text-indigo-400" />,
  },
  {
    id: 'otel',
    name: 'OpenTelemetry',
    category: 'Distributed Tracing',
    description: 'End-to-end W3C trace context across microservice RPC boundaries.',
    icon: <Radio className="w-6 h-6 text-emerald-400" />,
  },
  {
    id: 'datadog',
    name: 'Datadog APM',
    category: 'Cloud Telemetry',
    description: 'Direct ingestion of live agent events, custom metrics, and APM spans.',
    icon: <Cpu className="w-6 h-6 text-purple-400" />,
  },
  {
    id: 'grafana',
    name: 'Grafana',
    category: 'Dashboards',
    description: 'Bi-directional dashboard deep-linking and alert webhook ingestion.',
    icon: <Activity className="w-6 h-6 text-amber-400" />,
  },
  {
    id: 'kafka',
    name: 'Apache Kafka',
    category: 'Event Bus',
    description: 'High-throughput stream processing for risk events and incident alarms.',
    icon: <Zap className="w-6 h-6 text-cyan-400" />,
  },
  {
    id: 'postgres',
    name: 'PostgreSQL',
    category: 'State Store',
    description: 'ACID-compliant storage of incident histories and risk score drift.',
    icon: <Database className="w-6 h-6 text-indigo-400" />,
  },
  {
    id: 'redis',
    name: 'Redis',
    category: 'Cache & Pub/Sub',
    description: 'Sub-millisecond event streaming and distributed SSE pub/sub backend.',
    icon: <Layers className="w-6 h-6 text-rose-400" />,
  },
  {
    id: 'pagerduty',
    name: 'PagerDuty',
    category: 'On-Call Routing',
    description: 'Escalation routing and on-call paging for critical unmitigated alerts.',
    icon: <Shield className="w-6 h-6 text-emerald-400" />,
  },
  {
    id: 'ansible',
    name: 'Ansible Playbooks',
    category: 'Remediation',
    description: 'Safe YAML playbook execution for replica scale-outs and pod resets.',
    icon: <FileCode className="w-6 h-6 text-cyan-400" />,
  },
];

const allIntegrations = [...integrations, ...integrations];

export default function StackIntegrationsSection({ className }) {
  const scrollRef = useRef(null);
  const [isHovered, setIsHovered] = useState(false);
  const scrollPos = useRef(0);

  useEffect(() => {
    const scrollContainer = scrollRef.current;
    if (!scrollContainer) return;

    let animationFrameId;

    const autoScroll = () => {
      if (!isHovered) {
        scrollPos.current += 0.6;
        if (scrollPos.current >= scrollContainer.scrollWidth / 2) {
          scrollPos.current = 0;
        }
        scrollContainer.scrollLeft = scrollPos.current;
      } else {
        scrollPos.current = scrollContainer.scrollLeft;
      }
      animationFrameId = requestAnimationFrame(autoScroll);
    };

    animationFrameId = requestAnimationFrame(autoScroll);

    return () => cancelAnimationFrame(animationFrameId);
  }, [isHovered]);

  return (
    <section id="integrations" className={"dark:bg-slate-950 bg-slate-50 py-24 px-6 md:px-16 font-sans overflow-hidden border-t dark:border-white/[0.04] border-slate-200 transition-colors duration-300 " + (className || '')}>
      <div className="max-w-[1300px] mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-12">
          <div className="flex-1">
            <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider block mb-2">
              Ecosystem Connectivity
            </span>
            <h2
              className="font-bold text-3xl md:text-5xl dark:text-white text-slate-900 mb-2 leading-tight"
              style={{ fontFamily: "'Chakra Petch', sans-serif" }}
            >
              Works With Your Production Stack
            </h2>
            <p className="text-sm md:text-base dark:text-slate-400 text-slate-600">
              Zero agent friction. Out-of-the-box connectors for Kubernetes, Prometheus, and major cloud providers.
            </p>
          </div>
          <div className="px-4 py-2 rounded-full text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 border border-cyan-500/20">
            10+ Native Integrations Active
          </div>
        </div>

        {/* Marquee Carousel with Edge Fades */}
        <div className="relative">
          <div className="absolute left-0 top-0 bottom-0 w-24 md:w-36 bg-gradient-to-r dark:from-slate-950 dark:via-slate-950/80 from-slate-50 via-slate-50/80 to-transparent z-10 pointer-events-none" />
          <div className="absolute right-0 top-0 bottom-0 w-24 md:w-36 bg-gradient-to-l dark:from-slate-950 dark:via-slate-950/80 from-slate-50 via-slate-50/80 to-transparent z-10 pointer-events-none" />

          <div
            ref={scrollRef}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="flex flex-row gap-4 overflow-x-auto pb-4 no-scrollbar cursor-grab active:cursor-grabbing"
            style={{
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
            }}
          >
            {allIntegrations.map((item, index) => (
              <motion.div
                key={item.id + '-' + index}
                whileHover={{ y: -4 }}
                className="min-w-[240px] md:min-w-[280px] dark:bg-slate-900/60 bg-white border dark:border-white/10 border-slate-200 rounded-2xl p-6 flex flex-col justify-between transition-all duration-200 hover:border-cyan-500/50 dark:hover:bg-slate-900 hover:bg-slate-50/90 shadow-lg dark:shadow-black/30 shadow-slate-200/50 shrink-0"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-10 h-10 rounded-xl dark:bg-slate-800/80 bg-slate-100 border dark:border-white/10 border-slate-200 flex items-center justify-center">
                      {item.icon}
                    </div>
                    <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500 dark:bg-slate-800/60 bg-slate-100 px-2 py-0.5 rounded">
                      {item.category}
                    </span>
                  </div>

                  <h3 className="font-bold text-sm dark:text-white text-slate-900 mb-1">
                    {item.name}
                  </h3>
                  <p className="text-xs dark:text-slate-400 text-slate-600 leading-relaxed">
                    {item.description}
                  </p>
                </div>

                <div className="pt-4 border-t dark:border-white/[0.04] border-slate-100 mt-4 flex items-center justify-between text-[11px] font-mono text-cyan-600 dark:text-cyan-400">
                  <span>Native Driver</span>
                  <span>↗</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
