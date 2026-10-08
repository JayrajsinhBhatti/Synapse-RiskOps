/**
 * frontend/src/components/observability/ServiceMetricsViewer.jsx
 * 
 * Interactive Multi-Metric Telemetry Viewer.
 * Addresses UX Weakness #2 & P0 #2: Real metric visualization with time-range controls.
 * Supports: 15m, 1h, 6h, 24h, 7d time-series with SLA threshold bands,
 * multi-tab views (Latency, CPU/Memory, Error Rate, Connection Pool), and anomaly markers.
 */

import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import { useServiceMetrics } from '../../hooks/useAnalytics';
import {
  Activity,
  Clock,
  Cpu,
  Layers,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  BarChart2,
  Database,
} from 'lucide-react';

const TIME_RANGES = [
  { id: '15m', label: '15m' },
  { id: '1h', label: '1h' },
  { id: '6h', label: '6h' },
  { id: '24h', label: '24h' },
  { id: '7d', label: '7d' },
];

const METRIC_TABS = [
  { id: 'latency', label: 'Latency (p99/p95)', icon: Activity },
  { id: 'resources', label: 'CPU & Memory', icon: Cpu },
  { id: 'errors', label: 'Error Rate & QPS', icon: AlertTriangle },
  { id: 'pool', label: 'Connection Pool', icon: Database },
];

export default function ServiceMetricsViewer({
  serviceId,
  serviceName = 'payment-service',
  timeframe: initialTimeframe = '1h',
  onTimeframeChange,
}) {
  const [activeTab, setActiveTab] = useState('latency');
  const [internalTimeframe, setInternalTimeframe] = useState(initialTimeframe);

  const selectedTimeframe = onTimeframeChange ? initialTimeframe : internalTimeframe;

  const handleTimeframeSelect = (tf) => {
    if (onTimeframeChange) {
      onTimeframeChange(tf);
    } else {
      setInternalTimeframe(tf);
    }
  };

  const { data: metricsData, isLoading, refetch, isFetching } = useServiceMetrics({
    serviceId,
    serviceName,
    timeframe: selectedTimeframe,
  });

  const points = metricsData?.points || [];
  const thresholds = metricsData?.thresholds || {};

  // Custom Dark/Light Tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    return (
      <div className="bg-slate-900/95 dark:bg-slate-900/95 border border-slate-700/80 p-3 rounded-xl shadow-2xl backdrop-blur-md text-xs z-50">
        <div className="text-[11px] font-mono text-slate-400 mb-2 border-b border-slate-800 pb-1 flex items-center justify-between gap-4">
          <span>{label}</span>
          <span className="text-[10px] text-cyan-400 font-semibold">{serviceName}</span>
        </div>
        <div className="space-y-1">
          {payload.map((entry, idx) => (
            <div key={idx} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                {entry.name}:
              </span>
              <span className="font-mono font-bold text-white">
                {entry.value}
                {entry.name.includes('Rate') || entry.name.includes('CPU') || entry.name.includes('Memory') || entry.name.includes('Pool')
                  ? '%'
                  : entry.name.includes('Latency')
                  ? 'ms'
                  : ''}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="glass-card p-5 flex flex-col h-full">
      {/* Header Bar: Title, Service, Timeframe Controls */}
      <div className="flex items-center justify-between gap-4 mb-4 pb-3 border-b dark:border-white/[0.06] border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold dark:text-white text-slate-900">
                Service Telemetry & Metric Trends
              </h3>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-cyan-500/15 text-cyan-400 font-bold border border-cyan-500/20">
                {serviceName}
              </span>
            </div>
            <p className="text-[11px] dark:text-slate-400 text-slate-500">
              Live continuous telemetry with SLA threshold bands
            </p>
          </div>
        </div>

        {/* Time-Range Selector Buttons */}
        <div className="flex items-center gap-1.5">
          <div className="flex bg-slate-200/70 dark:bg-slate-900/80 p-0.5 rounded-lg border dark:border-slate-800 border-slate-300">
            {TIME_RANGES.map((tr) => (
              <button
                key={tr.id}
                onClick={() => handleTimeframeSelect(tr.id)}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all ${
                  selectedTimeframe === tr.id
                    ? 'bg-cyan-500 text-white shadow-sm'
                    : 'dark:text-slate-400 text-slate-600 hover:text-white'
                }`}
              >
                {tr.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-1.5 rounded-lg dark:bg-slate-900/80 bg-slate-200/70 hover:bg-slate-300 dark:hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Refresh metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metric Tabs */}
      <div className="flex items-center gap-2 mb-4">
        {METRIC_TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-synapse-500/20 text-cyan-400 border border-cyan-500/30 shadow-sm'
                  : 'dark:text-slate-400 text-slate-600 hover:text-white dark:hover:bg-slate-800/60 hover:bg-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Chart Canvas Area */}
      <div className="flex-1 w-full min-h-[240px] relative">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
              <span className="text-xs font-mono text-slate-400">Loading telemetry data...</span>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {activeTab === 'latency' ? (
              <AreaChart data={points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="p99Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="p95Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} unit="ms" />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <ReferenceLine
                  y={thresholds.latency_p99_sla_ms || 350}
                  stroke="#ef4444"
                  strokeDasharray="3 3"
                  label={{ value: 'SLA 350ms', fill: '#ef4444', fontSize: 10, position: 'top' }}
                />
                <Area
                  type="monotone"
                  dataKey="latency_p99"
                  name="p99 Latency"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#p99Grad)"
                />
                <Area
                  type="monotone"
                  dataKey="latency_p95"
                  name="p95 Latency"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#p95Grad)"
                />
              </AreaChart>
            ) : activeTab === 'resources' ? (
              <LineChart data={points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="timestamp" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} unit="%" domain={[0, 100]} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <ReferenceLine
                  y={thresholds.cpu_limit_pct || 85}
                  stroke="#f59e0b"
                  strokeDasharray="3 3"
                  label={{ value: 'Limit 85%', fill: '#f59e0b', fontSize: 10, position: 'top' }}
                />
                <Line
                  type="monotone"
                  dataKey="cpu_usage"
                  name="CPU Utilization"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="memory_usage"
                  name="Memory Utilization"
                  stroke="#ec4899"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            ) : activeTab === 'errors' ? (
              <AreaChart data={points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="errGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} unit="%" />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <ReferenceLine
                  y={thresholds.error_rate_sla_pct || 1.0}
                  stroke="#f43f5e"
                  strokeDasharray="3 3"
                  label={{ value: 'SLO 1.0%', fill: '#f43f5e', fontSize: 10, position: 'top' }}
                />
                <Area
                  type="monotone"
                  dataKey="error_rate"
                  name="5xx Error Rate"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#errGrad)"
                />
              </AreaChart>
            ) : (
              <LineChart data={points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="timestamp" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} unit="%" domain={[0, 100]} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <ReferenceLine
                  y={thresholds.connection_pool_warn_pct || 80}
                  stroke="#f59e0b"
                  strokeDasharray="3 3"
                  label={{ value: 'Warning 80%', fill: '#f59e0b', fontSize: 10, position: 'top' }}
                />
                <Line
                  type="monotone"
                  dataKey="connection_pool"
                  name="Connection Pool Saturation"
                  stroke="#a855f7"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        )}
      </div>

      {/* Summary Footer */}
      <div className="mt-3 pt-3 border-t dark:border-white/[0.06] border-slate-200 flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Resolution: {metricsData?.sample_interval || '120s'} step
        </span>
        <span className="font-mono">
          Threshold Breaches: {points.some((p) => p.error_rate > 1.0 || p.latency_p99 > 350) ? (
            <span className="text-red-400 font-bold">1 Active Alert</span>
          ) : (
            <span className="text-emerald-400 font-semibold">Nominal</span>
          )}
        </span>
      </div>
    </div>
  );
}
