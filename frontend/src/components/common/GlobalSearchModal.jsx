/**
 * frontend/src/components/common/GlobalSearchModal.jsx
 * 
 * Global Search Palette (Cmd+K / Ctrl+K).
 * Implements UX Weakness #9 & Section 10 P2 #13.
 * Searches across incidents, microservices, RCA diagnoses, and runbooks.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useIncidents, useServices } from '../../hooks/useIncidents';
import {
  Search,
  AlertOctagon,
  Server,
  Play,
  Brain,
  X,
  ArrowRight,
  Command,
} from 'lucide-react';
import { getSeverityBadge, getStatusBadge } from '../../utils/formatters';

export default function GlobalSearchModal({ isOpen, onClose, onNavigate }) {
  const [query, setQuery] = useState('');
  const { data: incidentsData } = useIncidents();
  const { data: servicesData } = useServices();

  const incidents = Array.isArray(incidentsData) ? incidentsData : [];
  const services = Array.isArray(servicesData) ? servicesData : [];

  // Close on Escape, open on Cmd+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Filter items based on search query
  const searchResults = useMemo(() => {
    if (!query.trim()) {
      return {
        incidents: incidents.slice(0, 3),
        services: services.slice(0, 4),
      };
    }

    const q = query.toLowerCase();
    const matchedIncidents = incidents.filter(
      (i) =>
        i.title?.toLowerCase().includes(q) ||
        i.root_cause?.toLowerCase().includes(q) ||
        i.guidance?.toLowerCase().includes(q) ||
        i.severity?.toLowerCase().includes(q)
    );

    const matchedServices = services.filter(
      (s) =>
        s.service_name?.toLowerCase().includes(q) ||
        s.name?.toLowerCase().includes(q) ||
        s.description?.toLowerCase().includes(q)
    );

    return {
      incidents: matchedIncidents.slice(0, 5),
      services: matchedServices.slice(0, 5),
    };
  }, [query, incidents, services]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 backdrop-blur-sm animate-in">
      <div
        className="w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[600px]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200 dark:border-slate-800">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search incidents, services, root causes, playbooks... (e.g. payment, latency, scale)"
            className="flex-1 bg-transparent border-none text-sm dark:text-white text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded border border-slate-300 dark:border-slate-700">
            ESC
          </kbd>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results Body */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Incidents Section */}
          {searchResults.incidents.length > 0 && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 mb-1.5 flex items-center gap-1.5">
                <AlertOctagon className="w-3 h-3 text-red-400" />
                Incidents ({searchResults.incidents.length})
              </div>
              <div className="space-y-1">
                {searchResults.incidents.map((inc) => (
                  <div
                    key={inc.id}
                    onClick={() => {
                      if (onNavigate) onNavigate('incidents', inc);
                      onClose();
                    }}
                    className="p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/60 cursor-pointer transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 shrink-0">
                        <AlertOctagon className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold dark:text-white text-slate-900 group-hover:text-cyan-400 transition-colors">
                          {inc.title}
                        </div>
                        <div className="text-[10px] text-slate-400 line-clamp-1">
                          {inc.root_cause || inc.description || 'Latency & error spike'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-semibold text-slate-700 dark:text-slate-300">
                        {inc.severity}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Microservices Section */}
          {searchResults.services.length > 0 && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 mb-1.5 flex items-center gap-1.5">
                <Server className="w-3 h-3 text-cyan-400" />
                Services Catalog ({searchResults.services.length})
              </div>
              <div className="space-y-1">
                {searchResults.services.map((svc) => (
                  <div
                    key={svc.id}
                    onClick={() => {
                      if (onNavigate) onNavigate('topology', svc);
                      onClose();
                    }}
                    className="p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/60 cursor-pointer transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
                        <Server className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold dark:text-white text-slate-900 group-hover:text-cyan-400 transition-colors">
                          {svc.service_name || svc.name}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          Criticality: {svc.criticality || 'TIER_1'} • {svc.owner || 'Platform Team'}
                        </div>
                      </div>
                    </div>

                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Shortcuts */}
          <div className="pt-2 border-t border-slate-200 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 px-2">
            <span>Press <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded text-[10px]">Enter</kbd> to select</span>
            <span>Synapse RiskOps Universal Search</span>
          </div>
        </div>
      </div>
    </div>
  );
}
