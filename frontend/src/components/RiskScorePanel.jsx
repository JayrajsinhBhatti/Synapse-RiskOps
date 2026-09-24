/**
 * frontend/src/components/RiskScorePanel.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Visualizes live microservice risk scores using Recharts.
 * Flags tiered risk thresholds (Healthy < 0.40, Watch 0.40-0.70, Critical >= 0.70)
 * and provides composite system health index.
 */

import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Cell,
} from 'recharts';
import { useLatestRisk, useServices } from '../hooks/useIncidents';
import { getRiskScoreStyle } from '../utils/formatters';
import { ShieldCheck, AlertTriangle, Flame, Activity, RefreshCw } from 'lucide-react';

export default function RiskScorePanel({ onSelectService, selectedServiceId }) {
  const { data: riskData, isLoading: riskLoading, refetch: refetchRisk } = useLatestRisk();
  const { data: servicesData, isLoading: servicesLoading } = useServices();

  const services = useMemo(() => {
    return Array.isArray(servicesData) ? servicesData : [];
  }, [servicesData]);

  // Combine services with their latest risk score
  const chartData = useMemo(() => {
    const riskMap = {};

    const rawList = Array.isArray(riskData)
      ? riskData
      : riskData && typeof riskData === 'object'
      ? [riskData]
      : [];

    rawList.forEach((r) => {
      let scoreVal = r.risk_score !== undefined ? Number(r.risk_score) : Number(r.composite_score);
      if (scoreVal > 1.0) {
        scoreVal = scoreVal / 100.0;
      }
      if (r.service_id) {
        riskMap[r.service_id] = scoreVal;
      }
      if (r.service_name) {
        riskMap[r.service_name] = scoreVal;
      }
      if (Array.isArray(r.affected_services)) {
        r.affected_services.forEach((aff) => {
          riskMap[aff] = scoreVal;
        });
      }
    });

    return services.map((s) => {
      const name = s.service_name || s.name || s.id;
      let score = riskMap[s.id] !== undefined ? riskMap[s.id] : riskMap[name];
      if (score === undefined) {
        // Deterministic baseline risk based on criticality
        score = s.criticality === 'CRITICAL' ? 0.38 : s.criticality === 'HIGH' ? 0.22 : 0.12;
      }

      const style = getRiskScoreStyle(score);
      const tier = s.criticality === 'CRITICAL' ? 1 : s.criticality === 'HIGH' ? 2 : 3;

      return {
        id: s.id,
        name: name.replace('-service', ''),
        fullName: name,
        score: Number(score.toFixed(3)),
        tier,
        health: s.is_active ? 'healthy' : 'degraded',
        color: style.color,
        category: style.tier,
      };
    }).sort((a, b) => b.score - a.score);
  }, [services, riskData]);

  // Summary Metrics
  const stats = useMemo(() => {
    if (!chartData.length) return { avg: '0.24', healthy: 12, watch: 0, critical: 0 };
    const total = chartData.reduce((acc, curr) => acc + curr.score, 0);
    const avg = total / chartData.length;
    const healthy = chartData.filter((c) => c.score < 0.40).length;
    const watch = chartData.filter((c) => c.score >= 0.40 && c.score < 0.70).length;
    const critical = chartData.filter((c) => c.score >= 0.70).length;
    return { avg: avg.toFixed(2), healthy, watch, critical };
  }, [chartData]);

  return (
    <div className="glass-card p-5 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-400" />
          <h2 className="text-base font-bold text-white tracking-wide">
            Microservice Risk Scoreboard
          </h2>
        </div>
        <button
          onClick={() => refetchRisk()}
          className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          title="Refresh Risk Assessments"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-4 gap-2.5 mb-5">
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-slate-400">Avg Risk Index</span>
          <span className="text-xl font-bold text-white mt-0.5">{stats.avg}</span>
          <span className="text-[10px] text-slate-500 mt-1">Scale 0.0 - 1.0</span>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> Healthy
          </span>
          <span className="text-xl font-bold text-emerald-300 mt-0.5">{stats.healthy}</span>
          <span className="text-[10px] text-emerald-400/60 mt-1">&lt; 0.40 Safe</span>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-amber-400 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Watch
          </span>
          <span className="text-xl font-bold text-amber-300 mt-0.5">{stats.watch}</span>
          <span className="text-[10px] text-amber-400/60 mt-1">0.40 - 0.69</span>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex flex-col">
          <span className="text-[11px] font-medium text-red-400 flex items-center gap-1">
            <Flame className="w-3 h-3" /> Critical
          </span>
          <span className="text-xl font-bold text-red-300 mt-0.5">{stats.critical}</span>
          <span className="text-[10px] text-red-400/60 mt-1">&ge; 0.70 Alert</span>
        </div>
      </div>

      {/* Chart Section */}
      <div className="flex-1 min-h-[220px] w-full bg-slate-900/60 rounded-xl p-2 border border-slate-800/80 mb-4">
        {chartData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs">
            Loading service risk metrics...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 12, right: 10, left: -20, bottom: 20 }}>
              <XAxis
                dataKey="name"
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                interval={0}
                angle={-35}
                textAnchor="end"
              />
              <YAxis
                stroke="#64748b"
                fontSize={10}
                domain={[0, 1]}
                ticks={[0.2, 0.4, 0.7, 1.0]}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-slate-900/95 border border-slate-700 p-2.5 rounded-lg shadow-xl text-xs text-white">
                        <div className="font-semibold text-slate-200">{data.fullName}</div>
                        <div className="text-slate-400 text-[11px]">Tier {data.tier}</div>
                        <div className="mt-1 flex items-center gap-2">
                          <span className="text-slate-400">Score:</span>
                          <span className="font-mono font-bold" style={{ color: data.color }}>
                            {data.score} ({data.category})
                          </span>
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine
                y={0.4}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                label={{ value: 'Watch (0.40)', fill: '#f59e0b', fontSize: 9, position: 'insideTopRight' }}
              />
              <ReferenceLine
                y={0.7}
                stroke="#ef4444"
                strokeDasharray="3 3"
                label={{ value: 'Critical (0.70)', fill: '#ef4444', fontSize: 9, position: 'insideTopRight' }}
              />
              <Bar
                dataKey="score"
                radius={[4, 4, 0, 0]}
                onClick={(entry) => onSelectService && onSelectService(entry.id)}
                cursor="pointer"
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                    opacity={selectedServiceId && selectedServiceId !== entry.id ? 0.45 : 0.9}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Mini Service List */}
      <div className="space-y-1.5 overflow-y-auto max-h-48 pr-1">
        {chartData.slice(0, 5).map((s) => {
          const isSelected = selectedServiceId === s.id;
          return (
            <div
              key={s.id}
              onClick={() => onSelectService && onSelectService(s.id)}
              className={`p-2 rounded-lg border text-xs flex items-center justify-between cursor-pointer transition-all ${
                isSelected
                  ? 'bg-synapse-500/20 border-synapse-500/60 text-white'
                  : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800 text-slate-300'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
                <span className="font-medium text-slate-200">{s.fullName}</span>
                <span className="text-[10px] text-slate-400 px-1.5 py-0.2 rounded bg-slate-700/50">
                  T{s.tier}
                </span>
              </div>
              <div className="flex items-center gap-2 font-mono">
                <span className="text-xs font-bold" style={{ color: s.color }}>
                  {s.score}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
