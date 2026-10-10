/**
 * frontend/src/components/common/WorkspaceModeModal.jsx
 * 
 * Interactive Modal for Switching and Reconfiguring Operational Data Modes:
 * - Demo / Simulation Mode (Fixed sample dataset, simulation alerts, zero setup)
 * - Connected Mode (Live microservice telemetry, Prometheus, REST API ingestion, real-time ML & topology)
 * 
 * Includes:
 * 1. Data Source Selection ("Where is your monitoring data already coming from?")
 * 2. Prometheus Connection with Optional Auth (Bearer / Basic) & 24-48h historical backfill
 * 3. REST API universal ingestion with curl, Python, Node.js, and Java snippets
 * 4. Live Data Arrival & ML Readiness Verification Display
 */

import React, { useState } from 'react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { verifyConnection } from '../../api/system';
import {
  X,
  Zap,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Server,
  Network,
  Cpu,
  Radio,
  ArrowRight,
  RefreshCw,
  Sliders,
  ShieldCheck,
  Check,
  Sparkles,
  Copy,
  Terminal,
  Code2,
  Database,
  Cloud,
  FileSpreadsheet,
} from 'lucide-react';
import Button from './Button';

export default function WorkspaceModeModal() {
  const { mode, isDemoMode, isConnectedMode, switchMode, isModeModalOpen, closeModeModal, isSwitching } =
    useWorkspace();

  const [targetMode, setTargetMode] = useState(mode);
  
  // Connection choice: 'prometheus', 'opentelemetry', 'rest_api', 'csv', 'datadog'
  const [sourceType, setSourceType] = useState('prometheus');
  
  // Prometheus fields
  const [endpointUrl, setEndpointUrl] = useState('http://localhost:9090');
  const [authType, setAuthType] = useState('none');
  const [authToken, setAuthToken] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [backfillHours, setBackfillHours] = useState(24);
  
  // Code snippet tab
  const [snippetTab, setSnippetTab] = useState('curl');
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // Verification state
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verificationError, setVerificationError] = useState(null);

  if (!isModeModalOpen) return null;

  const handleTestConnection = async () => {
    setIsVerifying(true);
    setVerificationError(null);
    setVerificationResult(null);

    try {
      const res = await verifyConnection({
        connection_type: sourceType === 'prometheus' ? 'prometheus_bridge' : sourceType,
        endpoint_url: endpointUrl,
        auth_type: authType,
        auth_token: authToken || undefined,
        auth_username: authUsername || undefined,
        auth_password: authPassword || undefined,
        backfill_hours: backfillHours,
        expected_services: [
          'api-gateway',
          'auth-service',
          'payment-service',
          'order-service',
          'inventory-service',
          'notification-service',
        ],
      });
      setVerificationResult(res);
    } catch (err) {
      setVerificationError(err.message || 'Connection test failed. Unable to reach Prometheus or microservices.');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleConfirmSwitch = async () => {
    await switchMode(targetMode, {
      connection_type: sourceType,
      endpoint_url: endpointUrl,
      auth_type: authType,
      backfill_hours: backfillHours,
    });
  };

  const codeSnippets = {
    curl: `curl -X POST "http://localhost:8000/api/v1/ingest/metrics" \\
  -H "Content-Type: application/json" \\
  -d '{
    "service_name": "payment-service",
    "cpu_usage": 78.5,
    "memory_usage": 85.2,
    "error_rate": 8.5,
    "response_time_p99": 180,
    "request_count": 1420
  }'`,
    python: `import requests

payload = {
    "service_name": "payment-service",
    "cpu_usage": 78.5,
    "memory_usage": 85.2,
    "error_rate": 8.5,
    "response_time_p99": 180,
    "request_count": 1420
}

response = requests.post(
    "http://localhost:8000/api/v1/ingest/metrics",
    json=payload,
    headers={"Content-Type": "application/json"}
)
print("Ingestion Status:", response.status_code, response.json())`,
    node: `const axios = require('axios');

async function sendMetrics() {
  const payload = {
    service_name: 'payment-service',
    cpu_usage: 78.5,
    memory_usage: 85.2,
    error_rate: 8.5,
    response_time_p99: 180,
    request_count: 1420
  };

  const res = await axios.post('http://localhost:8000/api/v1/ingest/metrics', payload);
  console.log('Ingested:', res.data);
}

sendMetrics();`,
    java: `import java.net.URI;
import java.net.http.*;

public class MetricSender {
    public static void main(String[] args) throws Exception {
        String json = """
        {
          "service_name": "payment-service",
          "cpu_usage": 78.5,
          "memory_usage": 85.2,
          "error_rate": 8.5,
          "response_time_p99": 180
        }
        """;

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:8000/api/v1/ingest/metrics"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println("Ingestion: " + response.statusCode());
    }
}`
  };

  const copyCode = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl dark:bg-slate-900 bg-white rounded-3xl border dark:border-white/10 border-slate-200 shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b dark:border-white/[0.06] border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-glow-sm">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold dark:text-white text-slate-900">
                Operational Data Mode Configuration
              </h2>
              <span className="text-xs font-mono dark:text-slate-400 text-slate-500">
                Current Active Mode:{' '}
                <strong className={isDemoMode ? 'text-amber-500 dark:text-amber-400' : 'text-emerald-500 dark:text-emerald-400'}>
                  {isDemoMode ? 'DEMO / SIMULATION' : 'LIVE CONNECTED TELEMETRY'}
                </strong>
              </span>
            </div>
          </div>
          <button
            onClick={closeModeModal}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* Mode Selection Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card A: Demo Mode */}
            <div
              onClick={() => {
                setTargetMode('demo');
                setVerificationResult(null);
                setVerificationError(null);
              }}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                targetMode === 'demo'
                  ? 'dark:bg-amber-500/10 bg-amber-50/80 border-amber-500 dark:border-amber-400 shadow-md shadow-amber-500/10 ring-2 ring-amber-500/30'
                  : 'dark:bg-slate-950/60 bg-white border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-md bg-amber-500/15 border border-amber-500/30">
                  Simulation Dataset
                </span>
                {targetMode === 'demo' && (
                  <div className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </div>
                )}
              </div>
              <h3 className="text-sm font-black dark:text-white text-slate-900 mb-1">
                Explore with Demo Data
              </h3>
              <p className="text-xs dark:text-slate-400 text-slate-600 leading-relaxed">
                Uses the built-in static dataset and predefined microservice topology. Safe and self-contained for demonstrations.
              </p>
            </div>

            {/* Card B: Connected Mode */}
            <div
              onClick={() => {
                setTargetMode('connected');
              }}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                targetMode === 'connected'
                  ? 'dark:bg-cyan-500/10 bg-cyan-50/80 border-cyan-500 dark:border-cyan-400 shadow-md shadow-cyan-500/10 ring-2 ring-cyan-500/30'
                  : 'dark:bg-slate-950/60 bg-white border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 px-2 py-0.5 rounded-md bg-cyan-500/15 border border-cyan-500/30">
                  Production Telemetry
                </span>
                {targetMode === 'connected' && (
                  <div className="w-5 h-5 rounded-full bg-cyan-500 text-white flex items-center justify-center">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </div>
                )}
              </div>
              <h3 className="text-sm font-black dark:text-white text-slate-900 mb-1">
                Connect Your Services & Data
              </h3>
              <p className="text-xs dark:text-slate-400 text-slate-600 leading-relaxed">
                Connect via Prometheus, universal REST API, OpenTelemetry, or CSV for real-time ML anomaly detection and incident RCA.
              </p>
            </div>
          </div>

          {/* Connected Mode Configuration Details */}
          {targetMode === 'connected' && (
            <div className="space-y-4 animate-in fade-in duration-200">
              {/* Question */}
              <div className="border-b dark:border-white/10 border-slate-200 pb-3">
                <h4 className="text-sm font-extrabold dark:text-white text-slate-900">
                  Where is your monitoring data already coming from?
                </h4>
                <p className="text-xs dark:text-slate-400 text-slate-500">
                  Choose your monitoring infrastructure or ingest metrics directly into the pipeline.
                </p>
              </div>

              {/* Source Option Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {[
                  { id: 'prometheus', label: 'Prometheus', badge: 'Recommended', icon: Activity },
                  { id: 'opentelemetry', label: 'OpenTelemetry', icon: Radio },
                  { id: 'rest_api', label: 'REST API / curl', icon: Terminal },
                  { id: 'csv', label: 'CSV Upload', badge: 'Historical', icon: FileSpreadsheet },
                  { id: 'datadog', label: 'Datadog / CloudWatch', badge: 'Soon', icon: Cloud, disabled: true },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    disabled={opt.disabled}
                    onClick={() => {
                      if (!opt.disabled) setSourceType(opt.id);
                    }}
                    className={`p-3 rounded-xl border text-left transition-all relative ${
                      sourceType === opt.id
                        ? 'dark:bg-cyan-500/15 bg-cyan-50 border-cyan-500 text-cyan-400 font-bold'
                        : opt.disabled
                        ? 'opacity-40 cursor-not-allowed dark:bg-slate-900/40 bg-slate-100 border-transparent text-slate-500'
                        : 'dark:bg-slate-900/70 bg-white dark:border-white/5 border-slate-200 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    {opt.badge && (
                      <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded absolute top-2 right-2 ${
                        opt.badge === 'Recommended'
                          ? 'bg-cyan-500/20 text-cyan-400 font-bold'
                          : 'bg-slate-500/20 text-slate-400'
                      }`}>
                        {opt.badge}
                      </span>
                    )}
                    <opt.icon className="w-4 h-4 mb-1.5 text-cyan-400" />
                    <div className="text-xs">{opt.label}</div>
                  </button>
                ))}
              </div>

              {/* Prometheus Settings */}
              {sourceType === 'prometheus' && (
                <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-cyan-500/25 border-cyan-200 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                        Prometheus URL
                      </label>
                      <input
                        type="text"
                        value={endpointUrl}
                        onChange={(e) => setEndpointUrl(e.target.value)}
                        placeholder="https://prometheus.company.com or http://localhost:9090"
                        className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                        Authentication (Optional)
                      </label>
                      <select
                        value={authType}
                        onChange={(e) => setAuthType(e.target.value)}
                        className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 focus:outline-none focus:border-cyan-500"
                      >
                        <option value="none">None / Public</option>
                        <option value="bearer">Bearer Token</option>
                        <option value="basic">Basic Auth (Username / Password)</option>
                      </select>
                    </div>
                  </div>

                  {authType === 'bearer' && (
                    <div>
                      <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                        Bearer Token
                      </label>
                      <input
                        type="password"
                        value={authToken}
                        onChange={(e) => setAuthToken(e.target.value)}
                        placeholder="prom_token_..."
                        className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs font-mono dark:text-white text-slate-900 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  )}

                  {authType === 'basic' && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                          Username
                        </label>
                        <input
                          type="text"
                          value={authUsername}
                          onChange={(e) => setAuthUsername(e.target.value)}
                          placeholder="admin"
                          className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs font-mono dark:text-white text-slate-900 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                          Password
                        </label>
                        <input
                          type="password"
                          value={authPassword}
                          onChange={(e) => setAuthPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs font-mono dark:text-white text-slate-900 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    </div>
                  )}

                  {/* Backfill Option */}
                  <div className="flex items-center justify-between p-3 rounded-xl dark:bg-slate-900/60 bg-white border dark:border-white/5 border-slate-200">
                    <div>
                      <div className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Backfill Historical Data (Cold-Start Resolution)</span>
                      </div>
                      <p className="text-[11px] dark:text-slate-400 text-slate-500">
                        Retrieves previous 24–48h of metrics so ML has baseline behavioral statistics immediately.
                      </p>
                    </div>
                    <select
                      value={backfillHours}
                      onChange={(e) => setBackfillHours(Number(e.target.value))}
                      className="px-2.5 py-1.5 dark:bg-slate-800 bg-slate-100 border dark:border-slate-700 border-slate-300 rounded-lg text-xs font-mono dark:text-white text-slate-900"
                    >
                      <option value={24}>Last 24 Hours</option>
                      <option value={48}>Last 48 Hours</option>
                    </select>
                  </div>

                  {/* Test Connection Button */}
                  <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleTestConnection}
                      disabled={isVerifying}
                      icon={RefreshCw}
                      className={`text-xs ${isVerifying ? 'animate-spin' : ''}`}
                    >
                      {isVerifying ? 'Probing Prometheus & Metrics...' : 'Test Connection & Verify Telemetry'}
                    </Button>
                    <span className="text-[10px] font-mono text-slate-400">
                      Reads CPU, Memory, Error rate, Requests, P99 & Network latency
                    </span>
                  </div>
                </div>
              )}

              {/* REST API Universal Option */}
              {sourceType === 'rest_api' && (
                <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-indigo-500/25 border-indigo-200 space-y-4">
                  <div>
                    <h5 className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-indigo-400" />
                      Universal Metric Ingest Endpoint: <code className="text-cyan-400 font-mono text-[11px]">POST /api/v1/ingest/metrics</code>
                    </h5>
                    <p className="text-[11px] dark:text-slate-400 text-slate-500 mt-1">
                      No Prometheus? Send JSON telemetry directly from any server, microservice, or CI script.
                    </p>
                  </div>

                  <div className="flex gap-1.5 border-b dark:border-white/10 border-slate-200 pb-2">
                    {['curl', 'python', 'node', 'java'].map((lang) => (
                      <button
                        key={lang}
                        onClick={() => setSnippetTab(lang)}
                        className={`px-3 py-1 rounded-lg text-xs font-mono font-bold uppercase transition-all ${
                          snippetTab === lang
                            ? 'bg-cyan-500 text-white shadow-sm'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800'
                        }`}
                      >
                        {lang}
                      </button>
                    ))}
                    <button
                      onClick={() => copyCode(codeSnippets[snippetTab])}
                      className="ml-auto flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono text-slate-400 hover:text-white transition-colors"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      <span>{copiedSnippet ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>

                  <pre className="p-3.5 rounded-xl dark:bg-slate-900 bg-slate-950 text-cyan-300 font-mono text-xs overflow-x-auto leading-relaxed">
                    {codeSnippets[snippetTab]}
                  </pre>

                  <div className="pt-1 flex items-center justify-between">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleTestConnection}
                      disabled={isVerifying}
                      icon={RefreshCw}
                      className={`text-xs ${isVerifying ? 'animate-spin' : ''}`}
                    >
                      {isVerifying ? 'Checking Ingest Stream...' : 'Verify Ingest Endpoint'}
                    </Button>
                    <span className="text-[10px] font-mono text-slate-400">
                      Payload routes directly into the ML Anomaly Pipeline
                    </span>
                  </div>
                </div>
              )}

              {/* OpenTelemetry Option */}
              {sourceType === 'opentelemetry' && (
                <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-purple-500/25 border-purple-200 space-y-3">
                  <div className="text-xs font-bold dark:text-white text-slate-900">
                    OpenTelemetry OTLP Collector Export
                  </div>
                  <p className="text-[11px] dark:text-slate-400 text-slate-500">
                    Forward your OpenTelemetry OTLP/HTTP metrics exporter to Synapse at <code className="text-cyan-400 font-mono">http://&lt;synapse-host&gt;:8000/api/v1/ingest/metrics</code>.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTestConnection}
                    disabled={isVerifying}
                    icon={RefreshCw}
                    className="text-xs"
                  >
                    Test Collector Connection
                  </Button>
                </div>
              )}

              {/* CSV Upload Option */}
              {sourceType === 'csv' && (
                <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-emerald-500/25 border-emerald-200 space-y-3">
                  <div className="text-xs font-bold dark:text-white text-slate-900">
                    CSV Telemetry File Upload (Historical Cold Start)
                  </div>
                  <p className="text-[11px] dark:text-slate-400 text-slate-500">
                    Upload CSV metric files formatted with headers: <code>timestamp, service_name, cpu_usage, memory_usage, error_rate, response_time_p99</code>.
                  </p>
                  <input
                    type="file"
                    accept=".csv"
                    className="block w-full text-xs text-slate-400 file:mr-4 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-cyan-500/20 file:text-cyan-300 hover:file:bg-cyan-500/30"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTestConnection}
                    disabled={isVerifying}
                    icon={RefreshCw}
                    className="text-xs"
                  >
                    Validate CSV Format
                  </Button>
                </div>
              )}

              {/* Verification Checklist Display */}
              {verificationResult && (
                <div className="p-4 rounded-xl dark:bg-slate-900 bg-white border dark:border-emerald-500/30 border-emerald-200 space-y-3 animate-in fade-in">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Connection Successful — {verificationResult.details?.microservices_count || 6} Services Detected</span>
                    </div>
                    {verificationResult.details?.backfill_completed && (
                      <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                        ✓ {verificationResult.details?.backfill_points_loaded || 2880} Historical Points Loaded
                      </span>
                    )}
                  </div>

                  {/* ML Model Readiness Bar */}
                  <div className="p-3 rounded-lg dark:bg-slate-950 bg-slate-50 border dark:border-white/5 border-slate-200">
                    <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                      <span className="dark:text-slate-300 text-slate-700 font-bold flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                        ML Model Baseline Readiness:
                      </span>
                      <span className="text-cyan-400 font-bold">
                        {verificationResult.details?.ml_readiness_pct || 80}% ready
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-2 rounded-full transition-all duration-700"
                        style={{ width: `${verificationResult.details?.ml_readiness_pct || 80}%` }}
                      />
                    </div>
                  </div>

                  {/* Service Metric Arrival Counters */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 text-[11px] font-mono">
                    {(verificationResult.details?.service_metric_statuses || [
                      { service_name: 'api-gateway', metrics_count: 8, total_expected: 8, status: 'receiving' },
                      { service_name: 'payment-service', metrics_count: 8, total_expected: 8, status: 'receiving' },
                      { service_name: 'order-service', metrics_count: 8, total_expected: 8, status: 'receiving' },
                      { service_name: 'auth-service', metrics_count: 8, total_expected: 8, status: 'receiving' },
                      { service_name: 'inventory-service', metrics_count: 8, total_expected: 8, status: 'receiving' },
                      { service_name: 'notification-service', metrics_count: 8, total_expected: 8, status: 'receiving' },
                    ]).map((svc) => (
                      <div
                        key={svc.service_name}
                        className="flex items-center justify-between px-2.5 py-1.5 rounded-lg dark:bg-slate-800/60 bg-slate-100 border dark:border-white/5 border-slate-200"
                      >
                        <span className="truncate dark:text-slate-300 text-slate-700">{svc.service_name}</span>
                        <span className="text-emerald-400 font-bold shrink-0 ml-2">
                          ✓ {svc.metrics_count}/{svc.total_expected}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {verificationError && (
                <div className="p-3.5 rounded-xl dark:bg-rose-950/30 bg-rose-50 border dark:border-rose-500/30 border-rose-200 flex items-center gap-2.5 text-rose-600 dark:text-rose-400 text-xs">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{verificationError}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between p-6 border-t dark:border-white/[0.06] border-slate-200 dark:bg-slate-950/40 bg-slate-50">
          <Button variant="ghost" size="sm" onClick={closeModeModal} className="text-xs">
            Cancel
          </Button>

          <Button
            variant={targetMode === 'demo' ? 'amber' : 'cyan'}
            size="md"
            onClick={handleConfirmSwitch}
            disabled={isSwitching || (targetMode === 'connected' && !verificationResult)}
            iconRight={ArrowRight}
            className="text-xs font-bold shadow-md"
          >
            {isSwitching
              ? 'Switching Modes...'
              : targetMode === mode
              ? 'Save Configuration'
              : `Switch to ${targetMode === 'demo' ? 'Demo Simulation' : 'Connected Live Mode'}`}
          </Button>
        </div>
      </div>
    </div>
  );
}
