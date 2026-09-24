/**
 * frontend/src/components/AuthModal.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Authentication Modal supporting standard username/password login
 * as well as 1-click Quick Login demo presets for Admin, SRE, and Operator roles.
 */

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Key, User, Lock, AlertCircle, CheckCircle, X } from 'lucide-react';

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(username, password);
      closeAuthModal();
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (u, p) => {
    setUsername(u);
    setPassword(p);
    setError(null);
    setIsSubmitting(true);
    try {
      await login(u, p);
      closeAuthModal();
    } catch (err) {
      setError(err.message || 'Quick login failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl p-6 text-slate-100">
        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-synapse-600/30 border border-synapse-500/40 flex items-center justify-center text-synapse-400">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Access Synapse RiskOps</h2>
            <p className="text-xs text-slate-400">Authenticate to execute remediation playbooks</p>
          </div>
        </div>

        {/* Quick Demo Login Presets */}
        <div className="mb-6">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
            1-Click Demo Profiles
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleQuickLogin('admin', 'admin123')}
              className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 transition-all text-center group"
            >
              <span className="text-xs font-bold text-purple-300 group-hover:scale-105 transition-transform">Admin</span>
              <span className="text-[10px] text-purple-400/80 mt-0.5">Full Control</span>
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('sre_lead', 'sre123')}
              className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 transition-all text-center group"
            >
              <span className="text-xs font-bold text-cyan-300 group-hover:scale-105 transition-transform">SRE Lead</span>
              <span className="text-[10px] text-cyan-400/80 mt-0.5">Remediate</span>
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('operator', 'operator123')}
              className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition-all text-center group"
            >
              <span className="text-xs font-bold text-emerald-300 group-hover:scale-105 transition-transform">Operator</span>
              <span className="text-[10px] text-emerald-400/80 mt-0.5">Read-Only</span>
            </button>
          </div>
        </div>

        <div className="relative flex items-center justify-center my-4">
          <div className="border-t border-slate-800 w-full" />
          <span className="bg-slate-900 px-3 text-[11px] text-slate-500 uppercase tracking-widest absolute">
            Or credentials
          </span>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Username</label>
            <div className="relative">
              <User className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. admin or sre_lead"
                className="w-full pl-9 pr-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-synapse-500 focus:ring-1 focus:ring-synapse-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-synapse-500 focus:ring-1 focus:ring-synapse-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-synapse-600 to-indigo-600 hover:from-synapse-500 hover:to-indigo-500 text-white font-medium text-sm shadow-lg shadow-synapse-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
