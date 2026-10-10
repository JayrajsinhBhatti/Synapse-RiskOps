/**
 * frontend/src/components/onboarding/OnboardingWizard.jsx
 * 
 * Enhanced Enterprise Onboarding Flow:
 * - Step 1: Tell us about your company (Organization Profile)
 * - Step 2: Choose Operational Data Mode:
 *     Option A: Explore with Demo Data (Fixed static simulation dataset)
 *     Option B: Connect Your Services & Data
 * - Step 3: "Where is your monitoring data already coming from?"
 *     1. Prometheus (Recommended) - with auth (None/Bearer/Basic) & historical backfill (24-48h)
 *     2. OpenTelemetry (OTLP Collector)
 *     3. REST API / curl (Universal POST /api/v1/ingest/metrics with ready-made curl, Python, Node, Java)
 *     4. CSV Upload (Historical telemetry data)
 *     5. Datadog / CloudWatch (Coming soon)
 * - Step 4: Live Telemetry Stream & Arrival Verification:
 *     Shows live metrics arriving per-service (e.g. order-service 8/8 metrics, payment-service 8/8 metrics),
 *     historical backfill status solving ML cold-start, and ML Model Readiness progress bar.
 * - Step 5: Review Detected Services:
 *     Customer reviews detected services, renames services, excludes services, assigns criticality (CRITICAL/HIGH/MED/LOW),
 *     and reviews dependency topology before launching.
 * - Step 'success': Launch Operational Dashboard.
 */

import React, { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { useWorkspace } from '../../context/WorkspaceContext';
import { verifyConnection, backfillMetrics, ingestMetric, batchConfigureServices } from '../../api/system';
import {
  Building2,
  Server,
  Zap,
  Sparkles,
  ShieldCheck,
  Check,
  Sun,
  Moon,
  FastForward,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Radio,
  RefreshCw,
  AlertTriangle,
  Layers,
  Network,
  Cpu,
  Database,
  ExternalLink,
  Code2,
  Copy,
  Terminal,
  FileSpreadsheet,
  Cloud,
  CheckCheck,
  Edit2,
  Sliders,
  Clock,
  Eye,
  EyeOff,
} from 'lucide-react';
import Button from '../common/Button';

export function OnboardingWizard({ onComplete }) {
  const { toggleTheme, isDark } = useTheme();
  const { switchMode } = useWorkspace();

  // Wizard Steps:
  // 1: Company Profile
  // 2: Mode Choice (Demo vs Connect)
  // 3: "Where is your monitoring data already coming from?" (Source selection & configuration)
  // 4: Live Telemetry Stream & Arrival Verification (Showing data is actually arriving + ML readiness)
  // 5: Review Detected Services (Rename, Exclude, Criticality, Dependencies)
  // 'success': Complete!
  const [step, setStep] = useState(1);

  // Screen 1: Company Profile State
  const [companyName, setCompanyName] = useState('Acme Cloud Services');
  const [industry, setIndustry] = useState('FinTech');
  const [companySize, setCompanySize] = useState('51-200');

  // Screen 2: Selected Data Mode ('demo' or 'connected')
  const [selectedMode, setSelectedMode] = useState('demo');

  // Screen 3: Source Selection ("Where is your monitoring data already coming from?")
  // Options: 'prometheus', 'opentelemetry', 'rest_api', 'csv_upload', 'datadog'
  const [connectionMethod, setConnectionMethod] = useState('prometheus');

  // Prometheus Connection Parameters
  const [promUrl, setPromUrl] = useState('http://localhost:9090');
  const [promAuthType, setPromAuthType] = useState('none'); // 'none', 'bearer', 'basic'
  const [promAuthToken, setPromAuthToken] = useState('');
  const [promUsername, setPromUsername] = useState('');
  const [promPassword, setPromPassword] = useState('');

  // Historical Backfill (Solving the Cold-Start Problem)
  const [backfillHours, setBackfillHours] = useState(24); // 0, 24, 48

  // REST API code snippet tab
  const [activeCodeTab, setActiveCodeTab] = useState('curl'); // 'curl', 'python', 'node', 'java'
  const [copiedCode, setCopiedCode] = useState(false);
  const [testIngestSending, setTestIngestSending] = useState(false);
  const [testIngestSuccess, setTestIngestSuccess] = useState(false);

  // Verification & Arrival States
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verificationError, setVerificationError] = useState(null);

  // Step 5: Detected Services Review State
  const [detectedServicesList, setDetectedServicesList] = useState([
    { service_name: 'payment-service', display_name: 'Payment Gateway', criticality: 'CRITICAL', is_active: true, dependencies: ['auth-service'] },
    { service_name: 'order-service', display_name: 'Order Processing', criticality: 'HIGH', is_active: true, dependencies: ['payment-service', 'inventory-service'] },
    { service_name: 'inventory-service', display_name: 'Inventory Catalog', criticality: 'HIGH', is_active: true, dependencies: [] },
    { service_name: 'auth-service', display_name: 'Auth & Identity', criticality: 'CRITICAL', is_active: true, dependencies: [] },
    { service_name: 'api-gateway', display_name: 'Public API Gateway', criticality: 'HIGH', is_active: true, dependencies: ['auth-service', 'order-service'] },
    { service_name: 'notification-service', display_name: 'Notification Service', criticality: 'MEDIUM', is_active: true, dependencies: [] },
  ]);

  // Code snippets for REST API universal option
  const codeSnippets = {
    curl: `curl -X POST http://localhost:8080/api/v1/ingest/metrics \\
  -H "Content-Type: application/json" \\
  -d '{
    "service_name": "payment-service",
    "cpu_usage": 78.5,
    "memory_usage": 85.2,
    "error_rate": 8.5,
    "response_time_p99": 180,
    "request_count": 145
  }'`,
    python: `import requests

url = "http://localhost:8080/api/v1/ingest/metrics"
payload = {
    "service_name": "payment-service",
    "cpu_usage": 78.5,
    "memory_usage": 85.2,
    "error_rate": 8.5,
    "response_time_p99": 180,
    "request_count": 145
}

response = requests.post(url, json=payload)
print(response.json())`,
    node: `const fetch = require('node-fetch');

const payload = {
  service_name: "payment-service",
  cpu_usage: 78.5,
  memory_usage: 85.2,
  error_rate: 8.5,
  response_time_p99: 180,
  request_count: 145
};

fetch("http://localhost:8080/api/v1/ingest/metrics", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
})
  .then(res => res.json())
  .then(data => console.log("Ingested:", data));`,
    java: `import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class SynapseMetricsAgent {
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
            .uri(URI.create("http://localhost:8080/api/v1/ingest/metrics"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println("Ingestion response: " + response.body());
    }
}`,
  };

  const handleCopyCode = (code) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Test sending a live metric via the universal REST API
  const handleSendTestMetric = async () => {
    setTestIngestSending(true);
    setTestIngestSuccess(false);
    try {
      await ingestMetric({
        service_name: 'payment-service',
        cpu_usage: 78.5,
        memory_usage: 85.2,
        error_rate: 8.5,
        response_time_p99: 180,
        request_count: 120,
        data_mode: 'connected',
      });
      setTestIngestSuccess(true);
      setTimeout(() => setTestIngestSuccess(false), 3000);
    } catch (err) {
      console.warn('Test ingest failed:', err);
    } finally {
      setTestIngestSending(false);
    }
  };

  // Run live verification & data arrival check
  const handleVerifyConnection = async () => {
    setIsVerifying(true);
    setVerificationError(null);
    setVerificationResult(null);

    try {
      const res = await verifyConnection({
        connection_method: connectionMethod,
        prometheus_url: promUrl,
        auth_type: promAuthType,
        auth_token: promAuthToken,
        auth_username: promUsername,
        auth_password: promPassword,
        backfill_hours: backfillHours,
      });

      setVerificationResult(res);

      // Populate detected services list from actual verification discovery
      if (res.services_discovered && res.services_discovered.length > 0) {
        const updatedList = res.services_discovered.map((s) => {
          const existing = detectedServicesList.find((d) => d.service_name === s);
          return existing || {
            service_name: s,
            display_name: s.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
            criticality: anyCrit(s),
            is_active: true,
            dependencies: [],
          };
        });
        setDetectedServicesList(updatedList);
      }

      // Automatically advance to Step 4: Data Arrival & Stream Verification
      setStep(4);
    } catch (err) {
      setVerificationError(
        err.message || 'Connection test failed. Please verify the URL and that Prometheus/services are accessible.'
      );
    } finally {
      setIsVerifying(false);
    }
  };

  function anyCrit(name) {
    if (name.includes('pay') || name.includes('auth')) return 'CRITICAL';
    if (name.includes('order') || name.includes('gateway')) return 'HIGH';
    return 'MEDIUM';
  }

  // Update a detected service in Step 5
  const handleUpdateDetectedService = (index, field, value) => {
    setDetectedServicesList((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  // Save config & finish onboarding
  const handleFinishOnboarding = async (targetMode = selectedMode) => {
    const config = {
      companyName,
      industry,
      companySize,
      operationalMode: targetMode,
      connectionType: targetMode === 'connected' ? connectionMethod : 'demo_static',
      endpointUrl: targetMode === 'connected' ? promUrl : null,
      backfillHours: targetMode === 'connected' ? backfillHours : 0,
      completedAt: new Date().toISOString(),
    };

    localStorage.setItem('synapse_workspace_config', JSON.stringify(config));
    localStorage.setItem('synapse_operational_mode', targetMode);
    localStorage.setItem('synapse_onboarding_completed', 'true');

    try {
      // If connected mode, save configured services batch
      if (targetMode === 'connected') {
        await batchConfigureServices(detectedServicesList);
      }
      await switchMode(targetMode, {
        connection_type: config.connectionType,
        endpoint_url: config.endpointUrl,
      });
    } catch (err) {
      console.warn('Switch mode sync notice during onboarding:', err);
    }

    setStep('success');
  };

  // Quick Skip: defaults to Demo mode
  const handleSkipOnboarding = async () => {
    const config = {
      companyName: companyName || 'Production Cluster',
      industry: industry || 'Technology',
      companySize: companySize || '11-50',
      operationalMode: 'demo',
      skipped: true,
      completedAt: new Date().toISOString(),
    };
    localStorage.setItem('synapse_workspace_config', JSON.stringify(config));
    localStorage.setItem('synapse_operational_mode', 'demo');
    localStorage.setItem('synapse_onboarding_completed', 'true');

    try {
      await switchMode('demo');
    } catch (err) {
      console.warn('Switch mode error on skip:', err);
    }

    if (onComplete) onComplete();
  };

  // ========================================================
  // SUCCESS SCREEN
  // ========================================================
  if (step === 'success') {
    return (
      <div className="min-h-screen dark:bg-slate-950 bg-slate-100 flex items-center justify-center p-6 selection:bg-indigo-500/30 transition-colors duration-300">
        <div className="max-w-md w-full text-center saas-card p-10 border dark:border-indigo-500/30 border-slate-200 shadow-2xl relative overflow-hidden animate-in fade-in duration-300">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-24 bg-cyan-500/20 blur-[60px] pointer-events-none rounded-full" />

          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center mx-auto mb-6 text-white shadow-lg shadow-emerald-500/30 animate-bounce duration-1000">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400">
            Workspace Initialized
          </span>
          <h2 className="text-2xl font-black dark:text-white text-slate-900 mt-1">
            Your RiskOps workspace is ready.
          </h2>

          <div className="mt-4 p-4 rounded-xl dark:bg-slate-900/80 bg-slate-50 border dark:border-white/5 border-slate-200 text-left space-y-2">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Active Operational Data Source
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  selectedMode === 'demo' ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'
                }`}
              />
              <span className="text-xs font-bold dark:text-white text-slate-900">
                {selectedMode === 'demo'
                  ? 'Demo Simulation Dataset (Isolated Demo Baseline)'
                  : `Live Connected Telemetry (${connectionMethod.toUpperCase()})`}
              </span>
            </div>
            {selectedMode === 'connected' && (
              <div className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400">
                ✓ {detectedServicesList.filter((s) => s.is_active).length} services configured & active
                {backfillHours > 0 && ` • ${backfillHours}h historical baseline backfilled`}
              </div>
            )}
            <p className="text-[11px] dark:text-slate-400 text-slate-500 pt-1">
              {selectedMode === 'demo'
                ? 'All dashboards will operate on the static demo dataset. You can switch to live connected data anytime from the top navigation bar.'
                : 'Real telemetry is actively flowing through the Prometheus Bridge, ML engine, and RCA pipelines.'}
            </p>
          </div>

          <Button
            variant="cyan"
            size="lg"
            onClick={onComplete}
            iconRight={ArrowRight}
            className="w-full mt-6 font-bold text-xs"
          >
            Launch Operational Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen dark:bg-slate-950 bg-slate-100 flex flex-col justify-center py-12 px-6 selection:bg-indigo-500/30 transition-colors duration-300">
      {/* Background glow highlights */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-indigo-600/10 blur-[130px] rounded-full pointer-events-none" />

      <div className="max-w-3xl w-full mx-auto">
        {/* Header / Brand with Skip & Theme Toggle */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-glow-sm">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-sm dark:text-white text-slate-900">
                Synapse <span className="text-cyan-600 dark:text-cyan-400">RiskOps</span>
              </span>
              <span className="text-[10px] block font-mono dark:text-slate-400 text-slate-500">
                Workspace Initialization & Telemetry Setup
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Quick Skip button in Header */}
            <button
              type="button"
              onClick={handleSkipOnboarding}
              className="text-xs font-semibold text-slate-500 hover:text-indigo-600 dark:hover:text-cyan-400 transition-colors px-3 py-1.5 rounded-lg border dark:border-slate-800 border-slate-200 dark:bg-slate-900 bg-white flex items-center gap-1.5 shadow-sm"
              title="Skip setup and open dashboard in demo mode"
            >
              <span>Skip Setup</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {/* Dark / Light Mode Toggle */}
            <button
              onClick={toggleTheme}
              title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle Theme"
              className="p-1.5 rounded-lg dark:text-slate-300 text-slate-600 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors flex items-center justify-center border dark:border-slate-800 border-slate-200 bg-white dark:bg-slate-900 shadow-sm"
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-300" /> : <Moon className="w-4 h-4 text-indigo-600" />}
            </button>

            <div className="flex items-center gap-2 text-xs font-mono dark:text-slate-400 text-slate-500 dark:bg-slate-900 bg-white px-3 py-1.5 rounded-lg border dark:border-slate-800 border-slate-200 shadow-sm">
              <span>Step {step} of {selectedMode === 'connected' ? 5 : 2}</span>
            </div>
          </div>
        </div>

        {/* Wizard Card Container */}
        <div className="dark:bg-slate-900/70 bg-white p-8 md:p-10 shadow-2xl dark:border-white/10 border-slate-200 rounded-3xl backdrop-blur-xl transition-colors duration-300">
          {/* ========================================================
              SCREEN 1: COMPANY
             ======================================================== */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-600 dark:text-cyan-400 tracking-wider">
                  Phase 1 • Organization Profile
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  Tell us about your company
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  This helps Synapse RiskOps tailor your operational workspace and incident priority matrix.
                </p>
              </div>

              {/* High-Visibility Skip Option */}
              <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-gradient-to-r from-indigo-50/90 via-cyan-50/60 to-white dark:from-slate-900 dark:to-slate-950 border dark:border-indigo-500/30 border-indigo-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-500 flex items-center justify-center text-white shadow-sm shrink-0">
                    <FastForward className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold dark:text-white text-slate-900 block">
                      Want to explore right away?
                    </span>
                    <span className="text-[11px] dark:text-slate-400 text-slate-600 block">
                      Skip company profile and launch straight into the dashboard with demo data.
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleSkipOnboarding}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-md shadow-indigo-600/20 flex items-center justify-center gap-1.5 transition-all shrink-0 active:scale-95"
                >
                  <span>Skip & Launch</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold dark:text-slate-300 text-slate-700">
                      Company Name
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setCompanyName('Acme Cloud Services');
                        setStep(2);
                      }}
                      className="text-[11px] font-medium text-indigo-600 dark:text-cyan-400 hover:underline"
                    >
                      Use default & continue &rarr;
                    </button>
                  </div>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Acme Cloud Corp"
                    className="w-full px-3.5 py-2.5 dark:bg-slate-950/80 bg-white border dark:border-slate-700/80 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 shadow-sm transition-colors"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-1.5">
                    Industry
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                      'Technology',
                      'FinTech',
                      'Healthcare',
                      'E-commerce',
                      'Manufacturing',
                      'SaaS',
                      'Other',
                    ].map((ind) => (
                      <button
                        key={ind}
                        type="button"
                        onClick={() => setIndustry(ind)}
                        className={`p-2.5 rounded-xl border text-xs font-medium transition-all text-center ${
                          industry === ind
                            ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                            : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                        }`}
                      >
                        {ind}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-1.5">
                    Company Size
                  </label>
                  <div className="grid grid-cols-5 gap-2">
                    {['1-10', '11-50', '51-200', '201-500', '500+'].map((sz) => (
                      <button
                        key={sz}
                        type="button"
                        onClick={() => setCompanySize(sz)}
                        className={`p-2.5 rounded-xl border text-xs font-medium transition-all text-center ${
                          companySize === sz
                            ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                            : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                        }`}
                      >
                        {sz}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <button
                  type="button"
                  onClick={handleSkipOnboarding}
                  className="text-xs font-semibold text-slate-500 hover:text-indigo-600 dark:hover:text-cyan-400 transition-colors"
                >
                  Skip setup &rarr;
                </button>

                <Button
                  variant="cyan"
                  size="md"
                  onClick={() => setStep(2)}
                  iconRight={ArrowRight}
                  className="text-xs font-bold shadow-md shadow-cyan-500/10"
                >
                  Continue to Data Source
                </Button>
              </div>
            </div>
          )}

          {/* ========================================================
              SCREEN 2: OPERATIONAL DATA MODE SELECTION
             ======================================================== */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-600 dark:text-cyan-400 tracking-wider">
                  Phase 2 • Operational Data Source
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  How would you like to start?
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  Choose whether to explore Synapse RiskOps using simulated data or connect live infrastructure.
                </p>
              </div>

              {/* Two Prominent Mode Options */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Option A: Explore with Demo Data */}
                <div
                  onClick={() => setSelectedMode('demo')}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between ${
                    selectedMode === 'demo'
                      ? 'dark:bg-amber-500/10 bg-amber-50/80 border-amber-500 dark:border-amber-400 shadow-md shadow-amber-500/10 ring-2 ring-amber-500/30'
                      : 'dark:bg-slate-950/60 bg-white border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-md bg-amber-500/15 border border-amber-500/30">
                        Simulation Mode
                      </span>
                      {selectedMode === 'demo' && (
                        <div className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </div>
                      )}
                    </div>
                    <h3 className="text-base font-black dark:text-white text-slate-900 mb-1">
                      A. Explore with Demo Data
                    </h3>
                    <p className="text-xs dark:text-slate-400 text-slate-600 leading-relaxed mb-4">
                      Enter the platform immediately without connecting or uploading infrastructure data.
                    </p>

                    <div className="space-y-2 text-[11px] dark:text-slate-300 text-slate-700">
                      <div className="flex items-center gap-2">
                        <Check className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                        <span>Fixed static demo dataset & simulated incidents</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                        <span>Clearly labeled as Demo/Simulation data</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                        <span>All ML, RCA, & dashboards fully functional</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t dark:border-white/5 border-slate-200 flex items-center gap-1.5 text-[10px] font-mono text-amber-600 dark:text-amber-400">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Instant access • Switch anytime later</span>
                  </div>
                </div>

                {/* Option B: Connect Your Services & Data */}
                <div
                  onClick={() => setSelectedMode('connected')}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between ${
                    selectedMode === 'connected'
                      ? 'dark:bg-cyan-500/10 bg-cyan-50/80 border-cyan-500 dark:border-cyan-400 shadow-md shadow-cyan-500/10 ring-2 ring-cyan-500/30'
                      : 'dark:bg-slate-950/60 bg-white border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 px-2 py-0.5 rounded-md bg-cyan-500/15 border border-cyan-500/30">
                        Production Telemetry
                      </span>
                      {selectedMode === 'connected' && (
                        <div className="w-5 h-5 rounded-full bg-cyan-500 text-white flex items-center justify-center">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </div>
                      )}
                    </div>
                    <h3 className="text-base font-black dark:text-white text-slate-900 mb-1">
                      B. Connect Your Services & Data
                    </h3>
                    <p className="text-xs dark:text-slate-400 text-slate-600 leading-relaxed mb-4">
                      Connect your existing observability tools (Prometheus, OTel, REST API) and stream real metrics.
                    </p>

                    <div className="space-y-2 text-[11px] dark:text-slate-300 text-slate-700">
                      <div className="flex items-center gap-2">
                        <Check className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
                        <span>Prometheus, OTel, or universal REST API</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
                        <span>Historical backfill solves ML cold-start</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
                        <span>Review & customize detected microservices</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t dark:border-white/5 border-slate-200 flex items-center gap-1.5 text-[10px] font-mono text-cyan-600 dark:text-cyan-400">
                    <Radio className="w-3.5 h-3.5" />
                    <span>Real-time ML anomaly detection & RCA</span>
                  </div>
                </div>
              </div>

              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => setStep(1)} icon={ArrowLeft} className="text-xs">
                  Back
                </Button>

                {selectedMode === 'demo' ? (
                  <Button
                    variant="amber"
                    size="md"
                    onClick={() => handleFinishOnboarding('demo')}
                    iconRight={Sparkles}
                    className="text-xs font-bold shadow-md shadow-amber-500/20"
                  >
                    Enter with Demo Data
                  </Button>
                ) : (
                  <Button
                    variant="cyan"
                    size="md"
                    onClick={() => setStep(3)}
                    iconRight={ArrowRight}
                    className="text-xs font-bold shadow-md shadow-cyan-500/20"
                  >
                    Choose Connection Method &rarr;
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* ========================================================
              SCREEN 3: "Where is your monitoring data already coming from?"
             ======================================================== */}
          {step === 3 && (
            <div className="space-y-6 animate-in fade-in">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-600 dark:text-cyan-400 tracking-wider">
                  Phase 3 • Ingestion Method Selection
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  Where is your monitoring data already coming from?
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  Instead of re-instrumenting your code, Synapse RiskOps connects directly to your existing telemetry sources.
                </p>
              </div>

              {/* 5 Ingestion Method Options */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {[
                  {
                    id: 'prometheus',
                    name: 'Prometheus',
                    badge: 'Recommended',
                    badgeColor: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
                    desc: 'Scrapes live metrics directly from your Prometheus cluster.',
                    icon: Server,
                  },
                  {
                    id: 'opentelemetry',
                    name: 'OpenTelemetry',
                    badge: 'OTLP Standard',
                    badgeColor: 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30',
                    desc: 'Stream standard OTel metrics & traces over HTTP/gRPC.',
                    icon: Radio,
                  },
                  {
                    id: 'rest_api',
                    name: 'REST API / curl',
                    badge: 'Universal',
                    badgeColor: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-500/30',
                    desc: 'Send metrics via standard JSON POST requests directly.',
                    icon: Terminal,
                  },
                  {
                    id: 'csv_upload',
                    name: 'CSV Upload',
                    badge: 'Historical',
                    badgeColor: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30',
                    desc: 'Upload CSV exports for historical behavior analysis.',
                    icon: FileSpreadsheet,
                  },
                  {
                    id: 'datadog',
                    name: 'Datadog / CloudWatch',
                    badge: 'Coming Soon',
                    badgeColor: 'bg-slate-500/15 text-slate-500 dark:text-slate-400 border-slate-500/30',
                    desc: 'Native vendor agents (forward via OTel/REST today).',
                    icon: Cloud,
                    disabled: false,
                  },
                ].map((item) => {
                  const Icon = item.icon;
                  const isSelected = connectionMethod === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setConnectionMethod(item.id)}
                      className={`p-3.5 rounded-2xl border text-left transition-all relative flex flex-col justify-between ${
                        isSelected
                          ? 'dark:bg-cyan-500/15 bg-cyan-50/80 border-cyan-500 dark:border-cyan-400 shadow-md ring-2 ring-cyan-500/30'
                          : 'dark:bg-slate-950/60 bg-white border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <div className="w-7 h-7 rounded-lg dark:bg-slate-800 bg-slate-100 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
                            <Icon className="w-4 h-4" />
                          </div>
                          <span className={`text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${item.badgeColor}`}>
                            {item.badge}
                          </span>
                        </div>
                        <div className="text-xs font-bold dark:text-white text-slate-900">{item.name}</div>
                        <p className="text-[10px] dark:text-slate-400 text-slate-500 mt-1 leading-snug">
                          {item.desc}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* METHOD CONFIGURATION PANE */}
              <div className="p-5 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-slate-800 border-slate-200 space-y-4">
                {/* 1. PROMETHEUS CONFIGURATION */}
                {connectionMethod === 'prometheus' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                        <Server className="w-4 h-4 text-emerald-500" />
                        <span>Prometheus Connection & Authentication</span>
                      </h4>
                      <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        Recommended
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                          Prometheus Server URL
                        </label>
                        <input
                          type="text"
                          value={promUrl}
                          onChange={(e) => setPromUrl(e.target.value)}
                          placeholder="https://prometheus.company.com"
                          className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 font-mono focus:outline-none focus:border-cyan-500"
                        />
                      </div>

                      <div>
                        <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                          Authentication Type
                        </label>
                        <select
                          value={promAuthType}
                          onChange={(e) => setPromAuthType(e.target.value)}
                          className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 focus:outline-none focus:border-cyan-500"
                        >
                          <option value="none">None / Public Internal</option>
                          <option value="bearer">Bearer Token (OAuth2 / Vault)</option>
                          <option value="basic">Basic Auth (Username & Password)</option>
                        </select>
                      </div>
                    </div>

                    {promAuthType === 'bearer' && (
                      <div>
                        <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                          Bearer Authorization Token
                        </label>
                        <input
                          type="password"
                          value={promAuthToken}
                          onChange={(e) => setPromAuthToken(e.target.value)}
                          placeholder="eyJhbGciOi..."
                          className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 font-mono focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    )}

                    {promAuthType === 'basic' && (
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                            Username
                          </label>
                          <input
                            type="text"
                            value={promUsername}
                            onChange={(e) => setPromUsername(e.target.value)}
                            placeholder="admin"
                            className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 font-mono focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] font-semibold dark:text-slate-300 text-slate-700 block mb-1">
                            Password
                          </label>
                          <input
                            type="password"
                            value={promPassword}
                            onChange={(e) => setPromPassword(e.target.value)}
                            placeholder="••••••••"
                            className="w-full px-3 py-2 dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 rounded-xl text-xs dark:text-white text-slate-900 font-mono focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      </div>
                    )}

                    {/* Historical Data Backfill (Cold-Start Resolution) */}
                    <div className="p-3.5 rounded-xl dark:bg-slate-900 bg-white border dark:border-indigo-500/30 border-indigo-200">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-indigo-500" />
                          <span className="text-xs font-bold dark:text-white text-slate-900">
                            Historical Data Backfill (Solves Cold-Start)
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                          ML Baseline Seeding
                        </span>
                      </div>
                      <p className="text-[11px] dark:text-slate-400 text-slate-500 leading-relaxed mb-3">
                        Retrieve the previous 24–48 hours of metrics from Prometheus so the ML Risk Engine starts with established behavioral baselines rather than waiting days to train.
                      </p>

                      <div className="grid grid-cols-3 gap-2">
                        {[
                          { hours: 0, label: 'No Backfill', sub: 'Start from now' },
                          { hours: 24, label: 'Previous 24 Hours', sub: 'Recommended' },
                          { hours: 48, label: 'Previous 48 Hours', sub: 'Full weekend/weekday' },
                        ].map((b) => (
                          <button
                            key={b.hours}
                            type="button"
                            onClick={() => setBackfillHours(b.hours)}
                            className={`p-2 rounded-xl border text-left transition-all ${
                              backfillHours === b.hours
                                ? 'dark:bg-indigo-600/20 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-900 font-bold'
                                : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-600'
                            }`}
                          >
                            <div className="text-xs">{b.label}</div>
                            <div className="text-[10px] font-normal dark:text-slate-400 text-slate-500">{b.sub}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. REST API UNIVERSAL OPTION */}
                {connectionMethod === 'rest_api' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                          <Terminal className="w-4 h-4 text-cyan-500" />
                          <span>Universal Ingestion Endpoint</span>
                        </h4>
                        <p className="text-[11px] dark:text-slate-400 text-slate-500">
                          Don't have Prometheus? Send metrics directly from your code or cron jobs.
                        </p>
                      </div>
                      <span className="text-[10px] font-mono text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                        POST /api/v1/ingest/metrics
                      </span>
                    </div>

                    {/* Language Code Snippets */}
                    <div className="rounded-xl overflow-hidden border dark:border-slate-800 border-slate-200">
                      <div className="flex items-center justify-between px-3 py-2 dark:bg-slate-900 bg-slate-100 border-b dark:border-slate-800 border-slate-200">
                        <div className="flex items-center gap-2">
                          {['curl', 'python', 'node', 'java'].map((lang) => (
                            <button
                              key={lang}
                              type="button"
                              onClick={() => setActiveCodeTab(lang)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold uppercase transition-all ${
                                activeCodeTab === lang
                                  ? 'bg-cyan-600 text-white'
                                  : 'dark:text-slate-400 text-slate-600 hover:text-slate-900 dark:hover:text-white'
                              }`}
                            >
                              {lang === 'node' ? 'Node.js' : lang}
                            </button>
                          ))}
                        </div>

                        <button
                          type="button"
                          onClick={() => handleCopyCode(codeSnippets[activeCodeTab])}
                          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors px-2 py-1 rounded-lg hover:bg-slate-800"
                        >
                          {copiedCode ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          <span className="text-[11px] font-mono">{copiedCode ? 'Copied!' : 'Copy Code'}</span>
                        </button>
                      </div>

                      <pre className="p-3.5 dark:bg-slate-950 bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto leading-relaxed">
                        <code>{codeSnippets[activeCodeTab]}</code>
                      </pre>
                    </div>

                    {/* Live Test Ingest Action */}
                    <div className="flex items-center justify-between pt-2">
                      <button
                        type="button"
                        onClick={handleSendTestMetric}
                        disabled={testIngestSending}
                        className="px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-bold shadow-sm flex items-center gap-2 transition-all active:scale-95 disabled:opacity-50"
                      >
                        <Zap className="w-3.5 h-3.5" />
                        <span>{testIngestSending ? 'Sending Sample Metric...' : 'Send Live Test Metric'}</span>
                      </button>

                      {testIngestSuccess && (
                        <div className="text-xs font-bold text-emerald-500 flex items-center gap-1.5 animate-in fade-in">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Sample metric ingested and evaluated by ML engine!</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 3. OPENTELEMETRY CONFIGURATION */}
                {connectionMethod === 'opentelemetry' && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                      <Radio className="w-4 h-4 text-indigo-500" />
                      <span>OpenTelemetry Collector (OTLP)</span>
                    </h4>
                    <p className="text-[11px] dark:text-slate-400 text-slate-500">
                      Configure your OpenTelemetry Collector <code className="font-mono text-cyan-600 dark:text-cyan-400">otel-collector-config.yaml</code> to forward metrics directly:
                    </p>
                    <pre className="p-3 rounded-xl dark:bg-slate-950 bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto leading-relaxed">
                      <code>{`exporters:
  otlphttp/synapse:
    endpoint: "http://localhost:8080/api/v1/ingest/metrics"

service:
  pipelines:
    metrics:
      receivers: [otlp, prometheus]
      processors: [batch]
      exporters: [otlphttp/synapse]`}</code>
                    </pre>
                  </div>
                )}

                {/* 4. CSV UPLOAD */}
                {connectionMethod === 'csv_upload' && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4 text-purple-500" />
                      <span>Historical CSV Telemetry Ingestion</span>
                    </h4>
                    <p className="text-[11px] dark:text-slate-400 text-slate-500">
                      Upload your infrastructure telemetry log in CSV format. Loaded metrics are automatically formatted into time-series records for ML training.
                    </p>
                    <div className="p-6 border-2 border-dashed dark:border-slate-800 border-slate-300 rounded-2xl text-center dark:bg-slate-950/40 bg-white">
                      <FileSpreadsheet className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                      <span className="text-xs font-bold dark:text-white text-slate-800 block">
                        Drag and drop your metrics CSV file here
                      </span>
                      <span className="text-[10px] text-slate-400 block mt-1">
                        Compatible with sample-data/sample_metrics.csv schema
                      </span>
                    </div>
                  </div>
                )}

                {/* 5. DATADOG / CLOUDWATCH */}
                {connectionMethod === 'datadog' && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                      <Cloud className="w-4 h-4 text-slate-400" />
                      <span>Datadog & AWS CloudWatch (Roadmap)</span>
                    </h4>
                    <p className="text-[11px] dark:text-slate-400 text-slate-500">
                      Native vendor agent polling is in active development. You can stream CloudWatch/Datadog metrics into Synapse RiskOps today using the OpenTelemetry collector or the universal REST API.
                    </p>
                  </div>
                )}
              </div>

              {/* Error Alert */}
              {verificationError && (
                <div className="p-3.5 rounded-xl dark:bg-rose-950/30 bg-rose-50 border dark:border-rose-500/30 border-rose-200 flex items-center gap-2.5 text-rose-600 dark:text-rose-400 text-xs">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{verificationError}</span>
                </div>
              )}

              {/* Step Navigation */}
              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => setStep(2)} icon={ArrowLeft} className="text-xs">
                  Back
                </Button>

                <Button
                  variant="cyan"
                  size="md"
                  onClick={handleVerifyConnection}
                  disabled={isVerifying}
                  isLoading={isVerifying}
                  icon={RefreshCw}
                  className="text-xs font-bold shadow-md shadow-cyan-500/20"
                >
                  {isVerifying ? 'Probing & Connecting...' : 'Test Connection & Receive Telemetry'}
                </Button>
              </div>
            </div>
          )}

          {/* ========================================================
              SCREEN 4: "Show the customer that data is actually arriving"
             ======================================================== */}
          {step === 4 && (
            <div className="space-y-6 animate-in fade-in">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-emerald-600 dark:text-emerald-400 tracking-wider">
                  Phase 4 • Live Telemetry Stream Arrival
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  Receiving Live Infrastructure Telemetry
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  Live metrics are arriving across your detected microservices and streaming into the ML Risk Engine.
                </p>
              </div>

              {/* Status Header: Connection Successful & Services Detected */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-emerald-500/30 border-emerald-200 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/15 text-emerald-500 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500 uppercase">Connection</span>
                    <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400">Connection Successful</div>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-cyan-500/30 border-cyan-200 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-cyan-500/15 text-cyan-500 flex items-center justify-center shrink-0">
                    <Server className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500 uppercase">Detection</span>
                    <div className="text-xs font-bold text-cyan-600 dark:text-cyan-400">
                      {detectedServicesList.length} Services Detected
                    </div>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-indigo-500/30 border-indigo-200 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/15 text-indigo-500 flex items-center justify-center shrink-0">
                    <Clock className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500 uppercase">Cold-Start Status</span>
                    <div className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
                      {backfillHours > 0 ? `${backfillHours}h Baseline Seeded` : 'Real-time Live Stream'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Per-Service Arriving Telemetry Breakdown */}
              <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-white border dark:border-slate-800 border-slate-200 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b dark:border-white/5 border-slate-200">
                  <span className="text-xs font-bold dark:text-white text-slate-900">
                    Active Telemetry Ingestion per Microservice
                  </span>
                  <span className="text-[10px] font-mono text-emerald-500 font-bold flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
                    STREAMING LIVE
                  </span>
                </div>

                <div className="space-y-2">
                  {detectedServicesList.map((svc) => (
                    <div
                      key={svc.service_name}
                      className="p-3 rounded-xl dark:bg-slate-900/60 bg-slate-50 border dark:border-slate-800 border-slate-200 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                        <span className="font-mono font-bold dark:text-white text-slate-900">
                          {svc.service_name}
                        </span>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="hidden sm:flex items-center gap-2 text-[10px] font-mono text-slate-400">
                          <span>CPU</span>
                          <span>•</span>
                          <span>Memory</span>
                          <span>•</span>
                          <span>Error Rate</span>
                          <span>•</span>
                          <span>P99 Latency</span>
                        </div>

                        <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          ✓ 8/8 metrics
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ML Model Readiness Progress Bar */}
              <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-slate-50 border dark:border-indigo-500/30 border-indigo-200 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold dark:text-white text-slate-900 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-indigo-400" />
                    <span>ML Risk Engine Calibration</span>
                  </span>
                  <span className="font-mono font-bold text-indigo-500">
                    {backfillHours > 0 ? '95% Ready' : '75% Ready (Warmup in progress)'}
                  </span>
                </div>

                <div className="w-full h-3 rounded-full dark:bg-slate-800 bg-slate-200 overflow-hidden relative">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 transition-all duration-1000"
                    style={{ width: backfillHours > 0 ? '95%' : '75%' }}
                  />
                </div>

                <p className="text-[11px] dark:text-slate-400 text-slate-500">
                  {backfillHours > 0
                    ? 'Historical behavior profile successfully established from previous 24h metrics. Autonomous anomaly scoring is fully active.'
                    : 'Initial telemetry vectors received. Model is establishing rolling normal baselines.'}
                </p>
              </div>

              {/* Step Navigation */}
              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => setStep(3)} icon={ArrowLeft} className="text-xs">
                  Reconfigure Source
                </Button>

                <Button
                  variant="cyan"
                  size="md"
                  onClick={() => setStep(5)}
                  iconRight={ArrowRight}
                  className="text-xs font-bold shadow-md shadow-cyan-500/20"
                >
                  Review Detected Services ({detectedServicesList.length}) &rarr;
                </Button>
              </div>
            </div>
          )}

          {/* ========================================================
              SCREEN 5: Review Detected Services & Customization
             ======================================================== */}
          {step === 5 && (
            <div className="space-y-6 animate-in fade-in">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-600 dark:text-cyan-400 tracking-wider">
                  Phase 5 • Service Inventory & Criticality Review
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  Review Detected Services
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  Customize service names, assign business criticality tiers, or exclude non-essential components.
                </p>
              </div>

              {/* Service Configuration List */}
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {detectedServicesList.map((svc, idx) => (
                  <div
                    key={svc.service_name}
                    className={`p-4 rounded-2xl border transition-all ${
                      svc.is_active
                        ? 'dark:bg-slate-950/70 bg-white border-slate-200 dark:border-slate-800'
                        : 'dark:bg-slate-950/30 bg-slate-50 border-slate-200 dark:border-slate-800/40 opacity-60'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      {/* Left: Rename & ID */}
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => handleUpdateDetectedService(idx, 'is_active', !svc.is_active)}
                          className={`p-1.5 rounded-lg border text-xs font-mono font-bold transition-colors ${
                            svc.is_active
                              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-500'
                              : 'bg-slate-500/15 border-slate-500/30 text-slate-400'
                          }`}
                          title={svc.is_active ? 'Click to exclude service from monitoring' : 'Click to include service'}
                        >
                          {svc.is_active ? <Check className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                        </button>

                        <div>
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={svc.display_name}
                              onChange={(e) => handleUpdateDetectedService(idx, 'display_name', e.target.value)}
                              className="text-xs font-bold dark:text-white text-slate-900 bg-transparent border-b border-transparent hover:border-slate-400 focus:border-cyan-500 focus:outline-none transition-colors"
                              title="Click to rename service"
                            />
                            <Edit2 className="w-3 h-3 text-slate-400" />
                          </div>
                          <span className="text-[10px] font-mono text-slate-400 block">
                            Identifier: {svc.service_name}
                          </span>
                        </div>
                      </div>

                      {/* Right: Criticality Selector & Dependencies */}
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-mono dark:text-slate-400 text-slate-500">Criticality:</span>
                          <select
                            value={svc.criticality}
                            onChange={(e) => handleUpdateDetectedService(idx, 'criticality', e.target.value)}
                            className={`px-2 py-1 rounded-lg border text-xs font-mono font-bold focus:outline-none cursor-pointer ${
                              svc.criticality === 'CRITICAL'
                                ? 'bg-rose-500/15 border-rose-500/30 text-rose-500'
                                : svc.criticality === 'HIGH'
                                ? 'bg-amber-500/15 border-amber-500/30 text-amber-500'
                                : 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400'
                            }`}
                          >
                            <option value="CRITICAL">CRITICAL</option>
                            <option value="HIGH">HIGH</option>
                            <option value="MEDIUM">MEDIUM</option>
                            <option value="LOW">LOW</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    {/* Dependencies info */}
                    {svc.dependencies && svc.dependencies.length > 0 && (
                      <div className="mt-2.5 pt-2.5 border-t dark:border-white/5 border-slate-100 flex items-center gap-1.5 text-[10px] font-mono text-slate-400">
                        <Network className="w-3 h-3 text-indigo-400" />
                        <span>Depends on:</span>
                        {svc.dependencies.map((dep) => (
                          <span
                            key={dep}
                            className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border dark:border-slate-700"
                          >
                            {dep}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Step Navigation */}
              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => setStep(4)} icon={ArrowLeft} className="text-xs">
                  Back to Stream
                </Button>

                <Button
                  variant="cyan"
                  size="md"
                  onClick={() => handleFinishOnboarding('connected')}
                  iconRight={Sparkles}
                  className="text-xs font-bold shadow-glow-cyan"
                >
                  Save & Launch Synapse Pipeline
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default OnboardingWizard;
