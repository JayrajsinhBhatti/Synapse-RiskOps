/**
 * frontend/src/layouts/DashboardLayout.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Main Application Shell & Cyber-Ops Layout.
 * Includes header with live system health indicators, SSE connection heartbeat,
 * view navigation tabs, simulation triggers, RBAC user profile, and Jayraj's Ops Chatbot.
 */

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useSSE } from '../hooks/useSSE';
import AuthModal from '../components/AuthModal';
import SimulateAlertModal from '../components/SimulateAlertModal';
import ChatWidget from '../components/chatbot/ChatWidget';
import {
  Shield,
  Activity,
  Zap,
  Radio,
  User,
  LogOut,
  LogIn,
  Layers,
  Network,
  AlertOctagon,
  BarChart3,
} from 'lucide-react';

export default function DashboardLayout({ activeView, onViewChange, children }) {
  const { user, isAuthenticated, role, logout, openAuthModal } = useAuth();
  const { isConnected, status: sseStatus } = useSSE();
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-synapse-500/30">
      {/* Top Application Header */}
      <header className="sticky top-0 z-40 bg-slate-900/80 backdrop-blur-xl border-b border-white/10 px-6 py-3">
        <div className="max-w-[1720px] mx-auto flex items-center justify-between gap-4">
          {/* Brand Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-synapse-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-synapse-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-black tracking-tight gradient-text">
                  Synapse RiskOps
                </h1>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-synapse-500/20 text-synapse-300 border border-synapse-500/30">
                  v0.6.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                Autonomous AI-Driven Microservice Reliability & Remediation
              </p>
            </div>
          </div>

          {/* Navigation View Switcher */}
          <nav className="flex items-center bg-slate-950/70 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => onViewChange('command-center')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeView === 'command-center'
                  ? 'bg-synapse-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Command Center
            </button>
            <button
              onClick={() => onViewChange('topology')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeView === 'topology'
                  ? 'bg-synapse-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Topology Map
            </button>
            <button
              onClick={() => onViewChange('incidents')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeView === 'incidents'
                  ? 'bg-synapse-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <AlertOctagon className="w-3.5 h-3.5" />
              Incidents & Audit
            </button>
            <button
              onClick={() => onViewChange('risk')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeView === 'risk'
                  ? 'bg-synapse-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Risk Analytics
            </button>
          </nav>

          {/* Right Toolbar: Live Indicators, Simulation, Auth */}
          <div className="flex items-center gap-3">
            {/* Live SSE Stream Pulse */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px]">
              <span className="relative flex h-2 w-2">
                {isConnected ? (
                  <>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </>
                ) : (
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500 animate-pulse" />
                )}
              </span>
              <span className={`font-mono font-medium ${isConnected ? 'text-emerald-400' : 'text-amber-400'}`}>
                {isConnected ? 'LIVE SSE' : 'RECONNECTING'}
              </span>
            </div>

            {/* Quick Simulate Button */}
            <button
              onClick={() => setIsSimulateModalOpen(true)}
              className="px-3 py-1.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 font-semibold text-xs flex items-center gap-1.5 shadow-sm transition-all"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Simulate Incident
            </button>

            {/* User Profile / Auth State */}
            {isAuthenticated ? (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
                <div className="flex items-center gap-2 bg-slate-800/80 px-2.5 py-1 rounded-xl border border-slate-700/60">
                  <User className="w-3.5 h-3.5 text-synapse-400" />
                  <span className="text-xs font-semibold text-slate-200">{user?.username}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                    role === 'ADMIN' ? 'bg-purple-500/30 text-purple-300' :
                    role === 'SRE' ? 'bg-cyan-500/30 text-cyan-300' :
                    'bg-slate-700 text-slate-300'
                  }`}>
                    {role}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-red-500/20 hover:text-red-400 text-slate-400 transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={openAuthModal}
                className="px-3.5 py-1.5 rounded-xl bg-synapse-600 hover:bg-synapse-500 text-white font-semibold text-xs shadow-md shadow-synapse-600/30 flex items-center gap-1.5 transition-all"
              >
                <LogIn className="w-3.5 h-3.5" />
                Sign In
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-[1720px] w-full mx-auto p-6">
        {children}
      </main>

      {/* Modals & Floating Elements */}
      <AuthModal />
      <SimulateAlertModal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
      />

      {/* Jayraj's Ops Chatbot Co-Pilot Widget */}
      <ChatWidget />
    </div>
  );
}
