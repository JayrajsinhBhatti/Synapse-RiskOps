/**
 * frontend/src/components/chatbot/cards/RiskScoreCard.jsx
 *
 * Visual card displaying service risk score gauge, risk tier badge, and prediction horizon.
 * Powers Feature #1: Service Health Query.
 */

import React from 'react';

export default function RiskScoreCard({ data }) {
  if (!data) return null;

  const {
    service_name = 'unknown-service',
    risk_score = 0,
    risk_tier = 'HEALTHY',
    prediction_confidence = 0.9,
    predicted_failure_type = 'none',
    prediction_horizon_minutes = 0,
    metrics = {},
  } = data;

  const tier = risk_tier.toUpperCase();
  const isCritical = tier === 'CRITICAL';
  const isWatch = tier === 'WATCH';

  const tierStyles = isCritical
    ? {
        border: 'border-red-500/40',
        bg: 'bg-red-500/10',
        badge: 'bg-red-500/20 text-red-400 border-red-500/30',
        scoreColor: 'text-red-400',
        accent: 'from-red-500 to-rose-600',
        dot: 'bg-red-400',
      }
    : isWatch
    ? {
        border: 'border-amber-500/40',
        bg: 'bg-amber-500/10',
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
        scoreColor: 'text-amber-400',
        accent: 'from-amber-500 to-yellow-600',
        dot: 'bg-amber-400',
      }
    : {
        border: 'border-emerald-500/40',
        bg: 'bg-emerald-500/10',
        badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        scoreColor: 'text-emerald-400',
        accent: 'from-emerald-500 to-teal-600',
        dot: 'bg-emerald-400',
      };

  return (
    <div
      className={`rounded-xl border p-4 my-2 backdrop-blur-md shadow-lg ${tierStyles.border} ${tierStyles.bg} transition-all duration-200`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${tierStyles.dot} animate-pulse`} />
          <h4 className="font-semibold text-white tracking-wide text-sm font-mono">
            {service_name}
          </h4>
        </div>
        <span
          className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${tierStyles.badge}`}
        >
          {tier}
        </span>
      </div>

      {/* Main Stats Row */}
      <div className="grid grid-cols-2 gap-4 py-3 items-center">
        {/* Risk Score Dial */}
        <div>
          <span className="text-xs text-gray-400 font-medium block mb-1">Risk Score</span>
          <div className="flex items-baseline gap-1.5">
            <span className={`text-3xl font-extrabold tracking-tight ${tierStyles.scoreColor}`}>
              {risk_score}
            </span>
            <span className="text-xs text-gray-500">/ 100</span>
          </div>
          <div className="w-full bg-white/10 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${tierStyles.accent}`}
              style={{ width: `${Math.min(100, Math.max(5, risk_score))}%` }}
            />
          </div>
        </div>

        {/* Prediction & Horizon */}
        <div className="text-xs space-y-1.5 pl-2 border-l border-white/10">
          <div>
            <span className="text-gray-400 block text-[11px]">Predicted Failure</span>
            <span className="font-mono text-gray-200 font-medium capitalize">
              {predicted_failure_type.replace(/_/g, ' ')}
            </span>
          </div>
          <div>
            <span className="text-gray-400 block text-[11px]">Prediction Horizon</span>
            <span className="text-gray-200 font-medium">
              {prediction_horizon_minutes > 0
                ? `In ~${prediction_horizon_minutes} minutes`
                : 'No failure imminent'}
            </span>
          </div>
          <div>
            <span className="text-gray-400 block text-[11px]">Confidence</span>
            <span className="text-gray-300 font-medium">
              {Math.round(prediction_confidence * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Vitals Grid */}
      {metrics && Object.keys(metrics).length > 0 && (
        <div className="grid grid-cols-4 gap-2 pt-3 mt-1 border-t border-white/10 text-center">
          <div className="bg-black/20 rounded p-1.5">
            <span className="text-[10px] text-gray-400 block">CPU</span>
            <span className="text-xs font-mono font-semibold text-gray-200">
              {metrics.cpu_usage ?? '—'}%
            </span>
          </div>
          <div className="bg-black/20 rounded p-1.5">
            <span className="text-[10px] text-gray-400 block">Memory</span>
            <span className="text-xs font-mono font-semibold text-gray-200">
              {metrics.memory_usage ?? '—'}%
            </span>
          </div>
          <div className="bg-black/20 rounded p-1.5">
            <span className="text-[10px] text-gray-400 block">Error Rate</span>
            <span className="text-xs font-mono font-semibold text-gray-200">
              {metrics.error_rate !== undefined ? `${(metrics.error_rate * 100).toFixed(1)}%` : '—'}
            </span>
          </div>
          <div className="bg-black/20 rounded p-1.5">
            <span className="text-[10px] text-gray-400 block">p99 Latency</span>
            <span className="text-xs font-mono font-semibold text-gray-200">
              {metrics.response_time_p99 ?? '—'}ms
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
