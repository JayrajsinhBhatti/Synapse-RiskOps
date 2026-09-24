/**
 * frontend/src/components/SimulateAlertModal.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Modal enabling developers and evaluators to inject synthetic or production-like
 * alert scenarios into the live backend pipeline and observe real-time SSE broadcasts.
 */

import React, { useState } from 'react';
import { useTriggerAlert } from '../hooks/useIncidents';
import { Zap, AlertTriangle, X, Check, Activity, Server } from 'lucide-react';

const SCENARIO_PRESETS = [
  {
    title: 'High CPU on Order Service',
    service_id: 'order-service',
    severity: 'HIGH',
    failure_type: 'HIGH_CPU',
    description: 'Order processing thread pool contention causing CPU spikes > 92% and queue stagnation.',
  },
  {
    title: 'Payment Gateway Latency Spike',
    service_id: 'payment-gateway',
    severity: 'CRITICAL',
    failure_type: 'LATENCY_SPIKE',
    description: 'Downstream payment provider API response times degraded to 4200ms, triggering cascading circuit breaks.',
  },
  {
    title: 'Inventory DB Connection Pool Saturation',
    service_id: 'inventory-service',
    severity: 'HIGH',
    failure_type: 'DB_POOL_EXHAUSTION',
    description: 'Database active connection pool reached 98% capacity; queries queueing and timing out.',
  },
];

export default function SimulateAlertModal({ isOpen, onClose }) {
  const triggerAlertMutation = useTriggerAlert();
  const [selectedService, setSelectedService] = useState('order-service');
  const [selectedSeverity, setSelectedSeverity] = useState('HIGH');
  const [failureType, setFailureType] = useState('HIGH_CPU');
  const [title, setTitle] = useState('High CPU on Order Service');
  const [description, setDescription] = useState(
    'Order processing thread pool contention causing CPU spikes > 92%.'
  );
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset) => {
    setSelectedService(preset.service_id);
    setSelectedSeverity(preset.severity);
    setFailureType(preset.failure_type);
    setTitle(preset.title);
    setDescription(preset.description);
    setSuccessMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccessMsg(null);
    try {
      await triggerAlertMutation.mutateAsync({
        service_id: selectedService,
        severity: selectedSeverity,
        title,
        description,
        failure_type: failureType,
        source: 'Frontend Simulation Trigger',
      });
      setSuccessMsg(`Incident successfully injected on ${selectedService}! SSE event broadcasted.`);
      setTimeout(() => {
        setSuccessMsg(null);
        onClose();
      }, 1500);
    } catch (err) {
      console.error('Failed to trigger alert:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl p-6 text-slate-100">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Simulate Anomaly / Alert</h2>
            <p className="text-xs text-slate-400">Inject an incident to test real-time SSE and remediation</p>
          </div>
        </div>

        {/* Presets */}
        <div className="mb-4">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
            Select Failure Scenario Preset
          </label>
          <div className="space-y-2">
            {SCENARIO_PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(p)}
                className={`w-full text-left p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between ${
                  title === p.title
                    ? 'bg-synapse-500/20 border-synapse-500/50 text-white shadow-sm'
                    : 'bg-slate-800/40 border-slate-700/60 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div>
                  <div className="font-semibold text-slate-200">{p.title}</div>
                  <div className="text-[11px] text-slate-400">{p.service_id} • {p.failure_type}</div>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  p.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'
                }`}>
                  {p.severity}
                </span>
              </button>
            ))}
          </div>
        </div>

        {successMsg && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
            <Check className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">Target Service</label>
              <input
                type="text"
                required
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
              />
            </div>
            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">Severity</label>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Incident Title</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
            />
          </div>

          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white resize-none"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={triggerAlertMutation.isPending}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-400 hover:to-rose-500 text-xs font-semibold text-white shadow-lg shadow-amber-500/20 disabled:opacity-50"
            >
              {triggerAlertMutation.isPending ? 'Injecting Incident...' : 'Trigger Incident Alert'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
