/**
 * frontend/src/components/RiskScorePanel.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Visualizes live microservice risk scores using Recharts.
 * Flags tiered risk thresholds (Healthy < 0.40, Watch 0.40-0.70, Critical >= 0.70)
 * and provides composite system health index.
 */

import React, { useMemo, useState } from 'react';
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
import { useLatestRisk, useServices, useIncidents } from '../hooks/useIncidents';
import { getRiskScoreStyle } from '../utils/formatters';
import { ShieldCheck, AlertTriangle, Flame, Activity, RefreshCw } from 'lucide-react';

export default function RiskScorePanel({ onSelectService, selectedServiceId }) {
  const { data: riskData, isLoading: riskLoading, refetch: refetchRisk } = useLatestRisk();
  const { data: servicesData, isLoading: servicesLoading } = useServices();
  const { data: incidentsData } = useIncidents();

  const [filterCategory, setFilterCategory] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const services = useMemo(() => {
    return Array.isArray(servicesData) ? servicesData : [];
  }, [servicesData]);

  // Combine services with their latest risk score & active incidents
  const chartData = useMemo(() => {
    const riskMap = {};

    const normalizeSvc = (val) =>
      String(val || '')
        .toLowerCase()
        .replace(/[-_\s]+/g, '')
        .replace('service', '')
        .replace('svc', '');

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
        riskMap[String(r.service_id)] = scoreVal;
      }
      if (r.service_name) {
        riskMap[r.service_name] = scoreVal;
        riskMap[normalizeSvc(r.service_name)] = scoreVal;
      }
      if (Array.isArray(r.affected_services)) {
        r.affected_services.forEach((aff) => {
          riskMap[aff] = scoreVal;
          riskMap[normalizeSvc(aff)] = scoreVal;
        });
      }
    });

    // Directly integrate active incident risk across all platform views
    const rawIncidents = Array.isArray(incidentsData) ? incidentsData : [];
    const activeIncidents = rawIncidents.filter(
      (i) => i.status === 'OPEN' || i.status === 'INVESTIGATING' || i.status === 'ACKNOWLEDGED' || i.status === 'REMEDIATING'
    );

    activeIncidents.forEach((inc) => {
      let scoreVal = inc.risk_score !== undefined ? Number(inc.risk_score) : 96.5;
      if (scoreVal > 1.0) scoreVal = scoreVal / 100.0;
      if (inc.service_id) {
        riskMap[String(inc.service_id)] = Math.max(scoreVal, riskMap[String(inc.service_id)] || 0);
      }
      if (inc.root_cause) {
        riskMap[inc.root_cause] = Math.max(scoreVal, riskMap[inc.root_cause] || 0);
        riskMap[normalizeSvc(inc.root_cause)] = Math.max(scoreVal, riskMap[normalizeSvc(inc.root_cause)] || 0);
      }
      if (Array.isArray(inc.affected_services)) {
        inc.affected_services.forEach((aff) => {
          const affScore = Math.max(0.68, scoreVal * 0.75);
          const affNorm = normalizeSvc(aff);
          if (riskMap[aff] === undefined || riskMap[aff] < 0.60) riskMap[aff] = affScore;
          if (riskMap[affNorm] === undefined || riskMap[affNorm] < 0.60) riskMap[affNorm] = affScore;
        });
      }
    });

    return services.map((s) => {
      const name = s.service_name || s.name || s.id;
      const norm = normalizeSvc(name);

      let score =
        riskMap[String(s.id)] !== undefined
          ? riskMap[String(s.id)]
          : riskMap[name] !== undefined
          ? riskMap[name]
          : riskMap[norm];

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
  }, [services, riskData, incidentsData]);

  // Filtered services for the breakdown list
  const filteredChartData = useMemo(() => {
    return chartData.filter((item) => {
      const matchesCategory =
        filterCategory === 'ALL' ||
        item.category.toUpperCase() === filterCategory.toUpperCase();
      const matchesSearch =
        !searchQuery.trim() ||
        item.fullName.toLowerCase().includes(searchQuery.toLowerCase().trim());
      return matchesCategory && matchesSearch;
    });
  }, [chartData, filterCategory, searchQuery]);

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
    <div className="glass-card p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
          <h2 className="text-base font-bold dark:text-white text-slate-900 tracking-wide">
            Microservice Risk Scoreboard
          </h2>
        </div>
        <button
          onClick={() => refetchRisk()}
          className="p-1.5 rounded-lg dark:bg-slate-800/80 bg-white dark:hover:bg-slate-700 hover:bg-slate-100 dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-950 border dark:border-transparent border-slate-200 shadow-sm transition-colors"
          title="Refresh Risk Assessments"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-4 gap-2.5 mb-5">
        <div className="dark:bg-slate-800/50 bg-slate-50 border dark:border-slate-700/60 border-slate-200 rounded-xl p-3 flex flex-col shadow-sm">
          <span className="text-[11px] font-semibold dark:text-slate-400 text-slate-500">Avg Risk Index</span>
          <span className="text-xl font-bold dark:text-white text-slate-900 mt-0.5">{stats.avg}</span>
          <span className="text-[10px] dark:text-slate-500 text-slate-400 mt-1">Scale 0.0 - 1.0</span>
        </div>
        <div className="dark:bg-emerald-500/10 bg-emerald-50 border dark:border-emerald-500/20 border-emerald-200 rounded-xl p-3 flex flex-col shadow-sm">
          <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> Healthy
          </span>
          <span className="text-xl font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">{stats.healthy}</span>
          <span className="text-[10px] text-emerald-600/70 dark:text-emerald-400/60 mt-1">&lt; 0.40 Safe</span>
        </div>
        <div className="dark:bg-amber-500/10 bg-amber-50 border dark:border-amber-500/20 border-amber-200 rounded-xl p-3 flex flex-col shadow-sm">
          <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Watch
          </span>
          <span className="text-xl font-bold text-amber-700 dark:text-amber-300 mt-0.5">{stats.watch}</span>
          <span className="text-[10px] text-amber-600/70 dark:text-amber-400/60 mt-1">0.40 - 0.69</span>
        </div>
        <div className="dark:bg-red-500/10 bg-red-50 border dark:border-red-500/20 border-red-200 rounded-xl p-3 flex flex-col shadow-sm">
          <span className="text-[11px] font-semibold text-red-600 dark:text-red-400 flex items-center gap-1">
            <Flame className="w-3 h-3" /> Critical
          </span>
          <span className="text-xl font-bold text-red-700 dark:text-red-300 mt-0.5">{stats.critical}</span>
          <span className="text-[10px] text-red-600/70 dark:text-red-400/60 mt-1">&ge; 0.70 Alert</span>
        </div>
      </div>

      {/* Chart Section */}
      <div className="h-[250px] w-full dark:bg-slate-900/60 bg-slate-50/60 rounded-xl p-2 border dark:border-slate-800/80 border-slate-200 mb-4 shadow-sm">
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

      {/* Services Risk List Section */}
      <div className="mt-2 pt-4 border-t dark:border-slate-800/80 border-slate-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider dark:text-slate-300 text-slate-700">
              Microservices Risk Breakdown
            </h3>
            <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full dark:bg-slate-800 bg-slate-200 dark:text-slate-300 text-slate-700">
              {filteredChartData.length} of {chartData.length} services
            </span>
          </div>

          {/* Filter and Search controls */}
          <div className="flex items-center gap-2">
            <div className="flex dark:bg-slate-800/80 bg-slate-100 p-0.5 rounded-lg border dark:border-slate-700/60 border-slate-200 text-[11px]">
              {['ALL', 'CRITICAL', 'WATCH', 'HEALTHY'].map((category) => (
                <button
                  key={category}
                  onClick={() => setFilterCategory(category)}
                  className={`px-2 py-0.5 rounded-md font-semibold transition-all ${
                    filterCategory === category
                      ? 'bg-synapse-600 text-white shadow-sm'
                      : 'dark:text-slate-400 text-slate-600 dark:hover:text-white hover:text-slate-900'
                  }`}
                >
                  {category === 'ALL' ? 'All' : category.charAt(0) + category.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder="Filter service..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-xs px-2.5 py-1 rounded-lg dark:bg-slate-900/80 bg-white border dark:border-slate-700 border-slate-300 dark:text-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-synapse-500 w-36"
            />
          </div>
        </div>

        {/* Expanded Services Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2.5 max-h-[340px] overflow-y-auto pr-1 pb-1">
          {filteredChartData.length === 0 ? (
            <div className="col-span-full py-6 text-center text-xs dark:text-slate-500 text-slate-400">
              No microservices match current filter.
            </div>
          ) : (
            filteredChartData.map((s) => {
              const isSelected = selectedServiceId === s.id || selectedServiceId === s.fullName;
              return (
                <div
                  key={s.id}
                  onClick={() => onSelectService && onSelectService(s.id)}
                  className={`p-2.5 rounded-xl border text-xs flex flex-col justify-between cursor-pointer transition-all duration-200 group shadow-sm ${
                    isSelected
                      ? 'dark:bg-synapse-900/30 bg-synapse-50 border-synapse-500 ring-1 ring-synapse-500/50 dark:text-white text-slate-950'
                      : 'dark:bg-slate-800/40 bg-white dark:border-slate-800 border-slate-200 hover:border-slate-300 dark:hover:border-slate-700 dark:hover:bg-slate-800/70 hover:bg-slate-50 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1.5 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                        style={{ backgroundColor: s.color }}
                      />
                      <span className="font-semibold truncate dark:text-slate-100 text-slate-900 text-xs">
                        {s.fullName}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded dark:bg-slate-800 bg-slate-100 text-slate-500 dark:text-slate-400 shrink-0">
                      T{s.tier}
                    </span>
                  </div>

                  {/* Progress bar and Risk Score */}
                  <div className="space-y-1 mt-auto">
                    <div className="w-full bg-slate-200 dark:bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(100, Math.max(8, s.score * 100))}%`,
                          backgroundColor: s.color,
                        }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[11px] pt-0.5">
                      <span
                        className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded"
                        style={{
                          color: s.color,
                          backgroundColor: `${s.color}15`,
                        }}
                      >
                        {s.category}
                      </span>
                      <span className="font-mono font-bold text-xs" style={{ color: s.color }}>
                        {s.score.toFixed(3)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
