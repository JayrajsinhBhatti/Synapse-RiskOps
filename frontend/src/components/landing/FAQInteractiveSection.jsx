/**
 * frontend/src/components/landing/FAQInteractiveSection.jsx
 * 
 * Interactive Tabbed Accordion FAQ section.
 * Implements user's FAQ02Kelo template with AnimatePresence smooth expand/collapse.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, X, Shield, Cpu, Terminal, ArrowRight } from 'lucide-react';

const faqData = {
  platform: [
    {
      question: 'How does the Graph Causal Engine pinpoint the true root cause?',
      answer: 'Synapse RiskOps models your microservices and dependencies as a directed acyclic graph (DAG). When anomalies surface, it executes backward causal traversal to distinguish the primary origin node from secondary symptom alerts downstream.',
    },
    {
      question: 'Does Synapse RiskOps require invasive cluster agents?',
      answer: 'No. The platform supports agentless ingestion via Prometheus scrape endpoints, OpenTelemetry collectors, and Kubernetes API webhooks. Setup takes under five minutes with zero cluster restart overhead.',
    },
    {
      question: 'How does real-time streaming work across network drops?',
      answer: 'The dashboard establishes a persistent Server-Sent Events (SSE) channel (/api/incidents/stream) with automatic exponential backoff reconnection and state reconciliation, ensuring zero lost telemetry events.',
    },
  ],
  safety: [
    {
      question: 'Can I enforce supervised human approvals before playbook execution?',
      answer: 'Yes. The Confidence Router enforces multi-tiered safety gates. Tier 1 (Confidence ≥ 85%) supports autonomous execution, while Tier 2 (60-84%) mandates explicit on-call SRE approval before any runbook runs.',
    },
    {
      question: 'Is telemetry encrypted and enterprise RBAC supported?',
      answer: 'All communication is encrypted via TLS 1.3 in transit and stored with AES-256 encryption. Role-Based Access Control (Admin, SRE, Operator) restricts remediation execution to authorized personnel only.',
    },
    {
      question: 'What happens if a remediation playbook fails?',
      answer: 'Every playbook execution is guarded by pre-flight health probes and an automatic timeout. If post-mitigation probes (/healthz) do not return HTTP 200 within 45s, the action rolls back and alerts the on-call engineer.',
    },
  ],
  operations: [
    {
      question: 'What remediation actions are supported out of the box?',
      answer: 'Synapse RiskOps includes production playbooks for Kubernetes Horizontal Pod Autoscaling (HPA), PostgreSQL connection pool purging, Canary traffic draining, and rolling memory leak restarts.',
    },
    {
      question: 'Can I interact with the platform using natural language?',
      answer: 'Yes! The integrated Ops Chatbot Copilot allows SREs to ask plain-English questions like "Why is order-service latency spiking?" or "What is the recommended runbook for high CPU?" directly within the console.',
    },
    {
      question: 'How can I simulate alerts to test the pipeline?',
      answer: 'The platform provides a built-in "Simulate Alert" trigger in the top toolbar to inject high-latency, memory leaks, and connection pool starvation scenarios into the ML engine with one click.',
    },
  ],
};

export default function FAQInteractiveSection({ onGetStarted, className }) {
  const [activeTab, setActiveTab] = useState('platform');
  const [openIndex, setOpenIndex] = useState(null);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setOpenIndex(null);
  };

  const toggleAccordion = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const tabs = [
    { id: 'platform', label: 'Platform & ML', icon: <Cpu className="w-4 h-4" /> },
    { id: 'safety', label: 'Security & Safety', icon: <Shield className="w-4 h-4" /> },
    { id: 'operations', label: 'Remediation & Ops', icon: <Terminal className="w-4 h-4" /> },
  ];

  return (
    <section id="faq" className={"dark:bg-slate-950 bg-slate-50 py-24 px-6 md:px-16 font-sans border-t dark:border-white/[0.04] border-slate-200 transition-colors duration-300 " + (className || '')}>
      <div className="max-w-[800px] mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider block mb-2">
            Technical Architecture FAQ
          </span>
          <h2
            className="text-3xl md:text-5xl font-bold dark:text-white text-slate-900 leading-tight mb-3"
            style={{ fontFamily: "'Chakra Petch', sans-serif" }}
          >
            All You Need to Know
          </h2>
          <p className="text-sm md:text-base dark:text-slate-400 text-slate-600">
            Answers to common questions about graph causality, safety tiers, and real-time operations.
          </p>
        </div>

        {/* Category Tabs */}
        <div className="flex justify-center gap-2 border-b dark:border-white/10 border-slate-200 mb-8 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={
                "inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold transition-all border-b-2 whitespace-nowrap " +
                (activeTab === tab.id
                  ? 'text-cyan-600 dark:text-cyan-400 border-cyan-500 bg-cyan-500/10 rounded-t-lg'
                  : 'dark:text-slate-400 text-slate-500 border-transparent dark:hover:text-white hover:text-slate-900')
              }
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Accordions */}
        <div className="space-y-0">
          {faqData[activeTab].map((item, index) => (
            <div key={index} className="border-b dark:border-white/[0.06] border-slate-200 py-5">
              <button
                onClick={() => toggleAccordion(index)}
                className="w-full flex justify-between items-center text-left cursor-pointer group"
              >
                <span className="text-sm md:text-base font-semibold dark:text-white text-slate-900 dark:group-hover:text-cyan-300 group-hover:text-cyan-600 transition-colors">
                  {item.question}
                </span>
                <span className="dark:text-slate-400 text-slate-500 transition-transform duration-300 pl-4 shrink-0">
                  {openIndex === index ? (
                    <X size={18} className="text-cyan-500 dark:text-cyan-400" />
                  ) : (
                    <Plus size={18} />
                  )}
                </span>
              </button>
              <AnimatePresence initial={false}>
                {openIndex === index && (
                  <motion.div
                    key={'faq-answer-' + index}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: 'easeOut' }}
                    className="overflow-hidden"
                  >
                    <div className="pt-3 pb-1 text-xs md:text-sm dark:text-slate-300 text-slate-600 leading-relaxed font-sans">
                      {item.answer}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>

        {/* Bottom Banner */}
        <div className="mt-12 dark:bg-slate-900/80 bg-white rounded-2xl p-6 md:p-8 border dark:border-white/10 border-slate-200 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl dark:shadow-2xl">
          <div>
            <h3 className="font-bold text-sm dark:text-white text-slate-900">Ready to inspect live cluster health?</h3>
            <p className="text-xs dark:text-slate-400 text-slate-500 mt-0.5">Explore the interactive command center with demo credentials.</p>
          </div>

          <button
            onClick={onGetStarted}
            className="rounded-full px-6 py-2.5 bg-gradient-to-r from-indigo-500 to-cyan-500 text-white font-bold text-xs hover:brightness-110 transition-all flex items-center gap-2 shadow-lg shadow-indigo-500/20"
          >
            <span>Launch Console</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </section>
  );
}
