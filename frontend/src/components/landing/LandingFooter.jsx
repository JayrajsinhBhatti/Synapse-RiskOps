/**
 * frontend/src/components/landing/LandingFooter.jsx
 * 
 * Minimal, sophisticated SaaS footer.
 */

import React from 'react';
import { Zap, Terminal, GitBranch } from 'lucide-react';

export function LandingFooter() {
  return (
    <footer id="about" className="border-t border-white/5 bg-slate-950 py-12 text-slate-400 text-xs">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-8 border-b border-white/5">
          {/* Logo & Tagline */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-cyan-400">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-sm text-white tracking-tight">
                Synapse <span className="text-cyan-400">RiskOps</span>
              </span>
              <p className="text-[11px] text-slate-400">
                Autonomous AI-Powered Risk Operations & Incident Intelligence
              </p>
            </div>
          </div>

          {/* Links */}
          <div className="flex flex-wrap items-center gap-6 font-medium text-slate-300">
            <a href="#how-it-works" className="hover:text-white transition-colors">Product</a>
            <a href="http://127.0.0.1:8080/docs" target="_blank" rel="noreferrer" className="hover:text-white transition-colors flex items-center gap-1">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              API Docs
            </a>
            <a href="#architecture" className="hover:text-white transition-colors">Architecture</a>
            <a href="https://github.com/JayrajsinhBhatti/Synapse-RiskOps" target="_blank" rel="noreferrer" className="hover:text-white transition-colors flex items-center gap-1">
              <GitBranch className="w-3.5 h-3.5" />
              GitHub
            </a>
          </div>
        </div>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400">
          <span>&copy; {new Date().getFullYear()} Synapse RiskOps Platform. All rights reserved.</span>
          <div className="flex items-center gap-4 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" /> Backend v0.6.0 Online
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default LandingFooter;
