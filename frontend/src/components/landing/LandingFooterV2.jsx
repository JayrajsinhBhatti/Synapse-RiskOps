/**
 * frontend/src/components/landing/LandingFooterV2.jsx
 * 
 * Immersive SaaS Footer with Reliability Brief Newsletter & Floating Glassmorphic bar.
 * Implements user's Footer04Kelo template tailored for Synapse RiskOps.
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Terminal, CheckCircle2 } from 'lucide-react';

export default function LandingFooterV2({ onLaunchApp, className }) {
  const [subscribed, setSubscribed] = useState(false);
  const [email, setEmail] = useState('');

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (email) {
      setSubscribed(true);
      setEmail('');
    }
  };

  const socialIcons = [
    {
      name: 'GitHub',
      href: 'https://github.com/JayrajsinhBhatti/Synapse-RiskOps',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
          <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
        </svg>
      ),
    },
    {
      name: 'API Docs',
      href: 'http://127.0.0.1:8080/docs',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      ),
    },
  ];

  return (
    <footer className={"w-full dark:bg-slate-950 bg-slate-100 pt-16 pb-8 font-sans transition-colors duration-300 " + (className || '')}>
      <div className="max-w-[1300px] mx-auto px-4">
        {/* Newsletter Hero Card */}
        <div className="rounded-[28px] overflow-hidden relative min-h-[380px] flex flex-col items-center justify-center p-8 md:p-14 border dark:border-white/10 border-slate-200/90 bg-gradient-to-b dark:from-indigo-950/40 dark:via-slate-900 dark:to-slate-950 from-indigo-50/70 via-white to-slate-50 shadow-2xl dark:shadow-black/50 shadow-slate-200/70 mb-8">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(79,70,229,0.15),transparent_70%)] pointer-events-none" />

          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-3xl md:text-5xl font-bold dark:text-white text-slate-900 text-center leading-tight tracking-tight relative z-10"
            style={{ fontFamily: "'Chakra Petch', sans-serif" }}
          >
            Weekly Reliability Brief. <br />
            <span className="text-cyan-500 dark:text-cyan-400 italic">No Fluff.</span>
          </motion.h2>

          <p className="text-xs md:text-sm dark:text-slate-400 text-slate-600 mt-3 text-center max-w-md relative z-10">
            Real-world post-mortems, graph causal algorithms, and automated SRE runbooks delivered weekly.
          </p>

          <motion.form
            onSubmit={handleSubscribe}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mt-8 w-full max-w-md h-14 dark:bg-slate-900/80 bg-white/95 backdrop-blur-xl rounded-full border dark:border-white/15 border-slate-200 flex p-1 shadow-2xl relative z-10"
          >
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter work email..."
              className="flex-1 bg-transparent px-5 text-xs dark:text-white text-slate-900 dark:placeholder:text-slate-500 placeholder:text-slate-400 outline-none border-none font-mono"
              required
            />
            <button
              type="submit"
              className="h-full px-6 bg-gradient-to-r from-indigo-500 to-cyan-500 text-white rounded-full text-xs font-bold tracking-wider uppercase hover:brightness-110 transition-all shrink-0 flex items-center gap-1.5"
            >
              {subscribed ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Subscribed</span>
                </>
              ) : (
                <span>Subscribe</span>
              )}
            </button>
          </motion.form>
        </div>

        {/* Floating Glassmorphic Footer Bar */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="dark:bg-slate-900/60 bg-white/90 backdrop-blur-2xl border dark:border-white/10 border-slate-200 rounded-2xl p-8 md:p-10 shadow-xl dark:shadow-2xl shadow-slate-200/60"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Column 1: Brand */}
            <div className="md:col-span-1">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-cyan-500 dark:text-cyan-400">
                  <Zap className="w-4 h-4" />
                </div>
                <span className="font-bold text-sm dark:text-white text-slate-900 tracking-tight">
                  Synapse <span className="text-cyan-500 dark:text-cyan-400">RiskOps</span>
                </span>
              </div>
              <p className="dark:text-slate-400 text-slate-600 text-xs leading-relaxed">
                Autonomous AI-Powered Risk Operations & Incident Intelligence. Built for high-reliability engineering teams.
              </p>
            </div>

            {/* Column 2: Architecture */}
            <div>
              <h4 className="dark:text-white text-slate-900 text-xs font-bold uppercase tracking-wider mb-3 font-mono">
                Architecture
              </h4>
              <ul className="space-y-2 text-xs dark:text-slate-400 text-slate-600">
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">Graph Causal Traversal</li>
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">ML RiskEngine Anomaly Scores</li>
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">Autonomous Playbook Router</li>
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">Server-Sent Events (SSE)</li>
              </ul>
            </div>

            {/* Column 3: Platform */}
            <div>
              <h4 className="dark:text-white text-slate-900 text-xs font-bold uppercase tracking-wider mb-3 font-mono">
                Platform
              </h4>
              <ul className="space-y-2 text-xs dark:text-slate-400 text-slate-600">
                <li>
                  <a href="http://127.0.0.1:8080/docs" target="_blank" rel="noreferrer" className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors flex items-center gap-1.5">
                    <Terminal className="w-3 h-3 text-cyan-500 dark:text-cyan-400" />
                    Interactive Swagger API
                  </a>
                </li>
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">Prometheus Integration</li>
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">Kubernetes Operators</li>
                <li className="dark:hover:text-cyan-300 hover:text-cyan-600 transition-colors cursor-pointer">Role-Based Access Control</li>
              </ul>
            </div>

            {/* Column 4: System Telemetry */}
            <div>
              <h4 className="dark:text-white text-slate-900 text-xs font-bold uppercase tracking-wider mb-3 font-mono">
                Cluster Status
              </h4>
              <div className="p-3 rounded-xl dark:bg-slate-950/80 bg-slate-50 border dark:border-white/10 border-slate-200 space-y-2 text-[11px] font-mono">
                <div className="flex items-center justify-between dark:text-slate-300 text-slate-700">
                  <span>Backend API:</span>
                  <span className="text-emerald-500 dark:text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> v0.6.0 Online
                  </span>
                </div>
                <div className="flex items-center justify-between dark:text-slate-300 text-slate-700">
                  <span>RiskEngine ML:</span>
                  <span className="text-emerald-500 dark:text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Port 8000
                  </span>
                </div>
                <div className="flex items-center justify-between dark:text-slate-300 text-slate-700">
                  <span>SSE Stream:</span>
                  <span className="text-cyan-600 dark:text-cyan-400">Heartbeat 15s</span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="mt-8 pt-5 border-t dark:border-white/10 border-slate-200 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs dark:text-slate-500 text-slate-600 font-mono">
            <span>&copy; {new Date().getFullYear()} Synapse RiskOps Platform. All rights reserved.</span>
            <div className="flex items-center gap-3">
              {socialIcons.map((social) => (
                <a
                  key={social.name}
                  href={social.href}
                  target="_blank"
                  rel="noreferrer"
                  className="w-8 h-8 rounded-full border dark:border-white/10 border-slate-200 flex items-center justify-center dark:hover:bg-white/10 hover:bg-slate-100 hover:border-cyan-500/50 transition-all dark:text-slate-300 text-slate-700"
                  aria-label={social.name}
                >
                  {social.icon}
                </a>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </footer>
  );
}
