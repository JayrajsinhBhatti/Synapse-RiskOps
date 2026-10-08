/**
 * frontend/src/layouts/DashboardLayout.jsx
 * 
 * Premium SaaS Application Shell with Sidebar Navigation.
 * Enhanced to address UX Weaknesses and Major Product Gaps:
 * - Universal Search Modal (Cmd+K / Ctrl+K)
 * - Notification Preferences & Webhook Integrations Hub
 * - Reliability Analytics Navigation
 * - Live SSE connection heartbeat
 * - RBAC user profile & dark/light theme toggle
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useSSE } from '../hooks/useSSE';
import AuthModal from '../components/AuthModal';
import SimulateAlertModal from '../components/SimulateAlertModal';
import ChatWidget from '../components/chatbot/ChatWidget';
import GlobalSearchModal from '../components/common/GlobalSearchModal';
import NotificationPreferencesModal from '../components/common/NotificationPreferencesModal';
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
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  Settings,
  HelpCircle,
  PanelLeftClose,
  PanelLeft,
  Home,
  Brain,
  Play,
  Server,
  History,
  Sun,
  Moon,
  Timer,
  Command,
  Flame,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const NAV_SECTIONS = [
  {
    heading: 'Operations',
    items: [
      { id: 'command-center', label: 'Command Center', icon: Layers, description: 'Unified telemetry & KPIs' },
      { id: 'chaos', label: 'Telemetry Proof (Demo)', icon: Flame, description: 'Live Before/After proof' },
      { id: 'incidents', label: 'Incidents & Audit', icon: AlertOctagon, description: 'Incident triage & history' },
      { id: 'topology', label: 'Topology Map', icon: Network, description: 'Service dependency graph' },
      { id: 'analytics', label: 'Reliability Analytics', icon: Timer, description: 'Computed MTTR & scorecard' },
    ],
  },
  {
    heading: 'Intelligence',
    items: [
      { id: 'risk', label: 'Risk Ranking', icon: BarChart3, description: 'Risk scores & telemetry' },
      { id: 'rca', label: 'Root Cause (RCA)', icon: Brain, description: 'Autonomous causal graph' },
      { id: 'risk-history', label: 'Risk History', icon: History, description: 'Model evaluations log' },
    ],
  },
  {
    heading: 'Automation',
    items: [
      { id: 'remediation', label: 'Runbooks & Remediation', icon: Play, description: 'Safe playbook execution' },
      { id: 'services', label: 'Services Catalog', icon: Server, description: 'Service mesh inventory' },
    ],
  },
];

const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) => s.items);

export default function DashboardLayout({ activeView, onViewChange, onLogout, children }) {
  const { user, isAuthenticated, role, logout, openAuthModal } = useAuth();
  const { isConnected, status: sseStatus } = useSSE();
  const { toggleTheme, isDark } = useTheme();
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [isNotificationsModalOpen, setIsNotificationsModalOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Global Keyboard Shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchModalOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLogout = () => {
    if (onLogout) onLogout();
    else logout();
  };

  return (
    <div className="min-h-screen dark:bg-slate-950 bg-slate-100 dark:text-slate-100 text-slate-900 flex font-sans selection:bg-synapse-500/30 transition-colors duration-300">
      {/* ================================================================
          SIDEBAR NAVIGATION
         ================================================================ */}
      <aside
        className={`fixed top-0 left-0 h-screen z-50 flex flex-col dark:bg-slate-900/95 bg-white/95 backdrop-blur-xl border-r dark:border-white/[0.06] border-slate-200 shadow-sm dark:shadow-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          sidebarCollapsed ? 'w-[68px]' : 'w-[240px]'
        }`}
      >
        {/* Sidebar Header / Logo */}
        <div className={`flex items-center gap-3 px-4 h-16 border-b dark:border-white/[0.06] border-slate-200 shrink-0 ${sidebarCollapsed ? 'justify-center' : ''}`}>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-synapse-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-synapse-500/20 shrink-0">
            <Zap className="w-4.5 h-4.5 text-white" />
          </div>
          {!sidebarCollapsed && (
            <div className="overflow-hidden">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-black tracking-tight dark:text-white text-slate-900 whitespace-nowrap">
                  Synapse
                </span>
                <span className="text-sm font-semibold text-cyan-600 dark:text-cyan-400 whitespace-nowrap">
                  RiskOps
                </span>
              </div>
              <span className="text-[10px] font-mono dark:text-slate-500 text-slate-400 whitespace-nowrap">
                v0.7.0 • Enterprise SRE
              </span>
            </div>
          )}
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-2.5 py-4 space-y-4 overflow-y-auto">
          {NAV_SECTIONS.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              {!sidebarCollapsed && (
                <span className="text-[10px] font-bold uppercase tracking-wider dark:text-slate-500 text-slate-400 px-2.5 mb-1.5 block">
                  {section.heading}
                </span>
              )}
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onViewChange(item.id)}
                    title={sidebarCollapsed ? item.label : undefined}
                    className={`group w-full flex items-center gap-3 rounded-xl transition-all duration-200 relative ${
                      sidebarCollapsed ? 'justify-center px-0 py-2.5' : 'px-3 py-2'
                    } ${
                      isActive
                        ? 'dark:bg-synapse-600/20 bg-synapse-50 text-synapse-700 dark:text-white font-semibold'
                        : 'dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-900 dark:hover:bg-white/[0.04] hover:bg-slate-100'
                    }`}
                  >
                    {/* Active indicator bar */}
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-synapse-500 shadow-glow-sm" />
                    )}
                    <Icon className={`w-[17px] h-[17px] shrink-0 transition-colors ${
                      isActive ? 'text-synapse-600 dark:text-synapse-400' : 'dark:text-slate-500 text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300'
                    }`} />
                    {!sidebarCollapsed && (
                      <div className="overflow-hidden text-left">
                        <span className={`text-xs block whitespace-nowrap ${
                          isActive ? 'dark:text-white text-synapse-900 font-bold' : 'font-medium'
                        }`}>
                          {item.label}
                        </span>
                        <span className="text-[10px] dark:text-slate-500 text-slate-400 block whitespace-nowrap truncate">
                          {item.description}
                        </span>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Sidebar Footer: Collapse Toggle + SSE Status */}
        <div className="shrink-0 px-2.5 pb-3 space-y-2">
          {/* SSE Connection Indicator */}
          <div className={`flex items-center gap-2 rounded-xl py-2 ${
            sidebarCollapsed ? 'justify-center px-0' : 'px-3 dark:bg-slate-950/60 bg-slate-50 border dark:border-slate-800/60 border-slate-200'
          }`}>
            <span className="relative flex h-2 w-2 shrink-0">
              {isConnected ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500 animate-pulse" />
              )}
            </span>
            {!sidebarCollapsed && (
              <span className={`text-[10px] font-mono font-medium ${isConnected ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                {isConnected ? 'LIVE STREAM' : 'RECONNECTING'}
              </span>
            )}
          </div>

          {/* Collapse Toggle */}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className={`w-full flex items-center gap-2 rounded-xl py-2 dark:text-slate-500 text-slate-400 dark:hover:text-slate-300 hover:text-slate-700 dark:hover:bg-white/[0.04] hover:bg-slate-100 transition-all ${
              sidebarCollapsed ? 'justify-center px-0' : 'px-3'
            }`}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? (
              <PanelLeft className="w-4 h-4" />
            ) : (
              <>
                <PanelLeftClose className="w-4 h-4" />
                <span className="text-[11px] font-medium">Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* ================================================================
          MAIN CONTENT AREA
         ================================================================ */}
      <div className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${
        sidebarCollapsed ? 'ml-[68px]' : 'ml-[240px]'
      }`}>
        {/* Top Application Header / Toolbar */}
        <header className="sticky top-0 z-40 dark:bg-slate-900/70 bg-white/90 backdrop-blur-xl border-b dark:border-white/[0.06] border-slate-200 px-6 h-14 flex items-center">
          <div className="w-full flex items-center justify-between gap-4">
            {/* Left: Breadcrumb / Page Title */}
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-bold dark:text-white text-slate-900">
                {ALL_NAV_ITEMS.find(n => n.id === activeView)?.label || 'Command Center'}
              </h2>
              <span className="text-[10px] font-mono dark:text-slate-500 text-slate-500 dark:bg-slate-800/60 bg-slate-100 border dark:border-transparent border-slate-200 px-2 py-0.5 rounded-md">
                {ALL_NAV_ITEMS.find(n => n.id === activeView)?.description || 'Unified operations view'}
              </span>
            </div>

            {/* Right: Actions, Search, Notifications & User Profile */}
            <div className="flex items-center gap-2">
              {/* Universal Search Button */}
              <button
                onClick={() => setIsSearchModalOpen(true)}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border dark:border-slate-800 border-slate-200 dark:bg-slate-900/60 bg-slate-50 dark:text-slate-400 text-slate-500 hover:text-slate-900 dark:hover:text-white text-xs transition-colors"
                title="Universal Search (Cmd+K)"
              >
                <Search className="w-3.5 h-3.5" />
                <span className="text-[11px] hidden sm:inline">Search...</span>
                <kbd className="text-[9px] font-mono px-1 py-0.5 rounded dark:bg-slate-800 bg-slate-200 text-slate-500">
                  ⌘K
                </kbd>
              </button>

              {/* Notification Preferences */}
              <button
                onClick={() => setIsNotificationsModalOpen(true)}
                className="p-1.5 rounded-lg border dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-600 hover:text-slate-900 dark:hover:text-white transition-colors"
                title="Notification & Webhook Preferences"
              >
                <Bell className="w-4 h-4" />
              </button>

              {/* Dark / Light Mode Toggle */}
              <button
                onClick={toggleTheme}
                title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
                aria-label="Toggle Theme"
                className="p-1.5 rounded-lg dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-900 dark:hover:bg-slate-800 hover:bg-slate-100 transition-colors flex items-center justify-center border dark:border-slate-800 border-slate-200"
              >
                {isDark ? (
                  <Sun className="w-3.5 h-3.5 text-amber-300" />
                ) : (
                  <Moon className="w-3.5 h-3.5 text-cyan-600" />
                )}
              </button>

              {/* Simulate Incident */}
              <button
                onClick={() => setIsSimulateModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/25 text-amber-500 dark:text-amber-300 font-semibold text-[11px] flex items-center gap-1.5 transition-all"
              >
                <Zap className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
                Simulate
              </button>

              {/* Divider */}
              <div className="h-6 w-px dark:bg-slate-800 bg-slate-200 mx-1" />

              {/* User Profile / Auth State */}
              {isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-2 dark:bg-slate-800/60 bg-slate-100 pl-1.5 pr-2.5 py-1 rounded-lg border dark:border-slate-700/50 border-slate-200">
                    <div className="w-6 h-6 rounded-md bg-gradient-to-br from-synapse-500 to-indigo-600 flex items-center justify-center text-white text-[10px] font-bold shrink-0">
                      {user?.username?.[0]?.toUpperCase() || 'U'}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] font-semibold dark:text-slate-200 text-slate-800">{user?.username}</span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider ${
                        role === 'ADMIN' ? 'bg-purple-500/25 text-purple-400 dark:text-purple-300 border border-purple-500/30' :
                        role === 'SRE' ? 'bg-cyan-500/25 text-cyan-600 dark:text-cyan-300 border border-cyan-500/30' :
                        'dark:bg-slate-700/60 bg-slate-200 dark:text-slate-300 text-slate-700 border dark:border-slate-600/30 border-slate-300'
                      }`}>
                        {role}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-red-500/15 hover:text-red-500 dark:hover:text-red-400 transition-all"
                    title="Sign Out"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={openAuthModal}
                  className="px-3.5 py-1.5 rounded-lg bg-synapse-600 hover:bg-synapse-500 text-white font-semibold text-[11px] shadow-md shadow-synapse-600/30 flex items-center gap-1.5 transition-all"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  Sign In
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-6 max-w-[1720px] w-full mx-auto">
          {children}
        </main>
      </div>

      {/* Modals & Floating Elements */}
      <AuthModal />
      <SimulateAlertModal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
      />
      <GlobalSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onNavigate={(viewId) => {
          onViewChange(viewId);
        }}
      />
      <NotificationPreferencesModal
        isOpen={isNotificationsModalOpen}
        onClose={() => setIsNotificationsModalOpen(false)}
      />

      {/* Jayraj's Ops Chatbot Co-Pilot Widget */}
      <ChatWidget />
    </div>
  );
}
