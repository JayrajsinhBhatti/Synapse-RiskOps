/**
 * frontend/src/components/common/ConnectWebsiteModal.jsx
 * 
 * Interactive Modal for Admin Connection & Management of the
 * External 10-Microservice E-Commerce Application.
 * 
 * Features:
 * - Real-time connectivity probe to API Gateway (port 9101)
 * - Service topology catalog of the 10 microservices
 * - Strict ADMIN role enforcement for Connect / Disconnect actions
 * - Live status indicators and 1-click Storefront UI launcher
 */

import React, { useState } from 'react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { useAuth } from '../../context/AuthContext';
import {
  X,
  Globe,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Server,
  Layers,
  ArrowRight,
  RefreshCw,
  ExternalLink,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Power,
  PowerOff,
  ShoppingBag,
  Cpu,
  Activity,
} from 'lucide-react';
import Button from './Button';

const MICROSERVICES_LIST = [
  { name: 'api-gateway', port: 9101, role: 'Edge Router & Traffic Dispatcher', criticality: 'CRITICAL' },
  { name: 'auth-service', port: 9102, role: 'JWT Authentication & Identity', criticality: 'CRITICAL' },
  { name: 'user-service', port: 9103, role: 'User Profile & Account Store', criticality: 'HIGH' },
  { name: 'catalog-service', port: 9104, role: 'Product Catalog & Inventory Details', criticality: 'HIGH' },
  { name: 'inventory-service', port: 9105, role: 'Warehouse Stock & Atomic Reservation', criticality: 'HIGH' },
  { name: 'cart-service', port: 9106, role: 'Shopping Cart State & Aggregation', criticality: 'HIGH' },
  { name: 'order-service', port: 9107, role: 'Distributed Checkout Coordinator', criticality: 'HIGH' },
  { name: 'payment-service', port: 9108, role: 'Payment Simulation & Authorization', criticality: 'CRITICAL' },
  { name: 'notification-service', port: 9109, role: 'Order Receipts & Alerts Feed', criticality: 'MEDIUM' },
  { name: 'recommendation-service', port: 9110, role: 'AI Product Affinity & Suggestions', criticality: 'MEDIUM' },
];

export default function ConnectWebsiteModal() {
  const {
    isConnectModalOpen,
    closeConnectModal,
    mode,
    externalAppConnected,
    connectWebsite,
    disconnectWebsite,
    isSwitching,
  } = useWorkspace();

  const { role, isAdmin } = useAuth();

  const [gatewayUrl, setGatewayUrl] = useState('http://localhost:9101');
  const [storefrontUrl, setStorefrontUrl] = useState('http://localhost:9100');
  const [probeStatus, setProbeStatus] = useState(null); // 'idle' | 'probing' | 'online' | 'offline'
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  if (!isConnectModalOpen) return null;

  const isConnected = mode === 'connected' && externalAppConnected;

  const handleProbe = async () => {
    setProbeStatus('probing');
    setErrorMessage(null);
    try {
      const resp = await fetch(`${gatewayUrl}/health`, { method: 'GET' });
      if (resp.ok) {
        setProbeStatus('online');
      } else {
        setProbeStatus('offline');
        setErrorMessage(`Gateway responded with HTTP status ${resp.status}`);
      }
    } catch (err) {
      setProbeStatus('offline');
      setErrorMessage(`Cannot connect to Gateway at ${gatewayUrl}. Please run start_demo.bat.`);
    }
  };

  const handleConnect = async () => {
    if (!isAdmin) {
      setErrorMessage('Admin privileges are required to connect external applications.');
      return;
    }
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await connectWebsite(gatewayUrl);
      setSuccessMessage('Successfully connected 10 microservices to Synapse RiskOps! Live operational telemetry is now active.');
      setProbeStatus('online');
    } catch (err) {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to connect application.');
    }
  };

  const handleDisconnect = async () => {
    if (!isAdmin) {
      setErrorMessage('Admin privileges are required to disconnect external applications.');
      return;
    }
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await disconnectWebsite();
      setSuccessMessage('External application disconnected. Synapse RiskOps reverted to Demo mode.');
    } catch (err) {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to disconnect application.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl dark:bg-slate-900 bg-white rounded-3xl border dark:border-white/10 border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b dark:border-white/[0.06] border-slate-200 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-cyan-500 via-indigo-600 to-emerald-400 flex items-center justify-center text-white shadow-glow-sm">
              <Globe className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-black dark:text-white text-slate-900">
                  External Website & Microservices Platform
                </h2>
                <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full border ${
                  isConnected
                    ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                    : 'bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-400'
                }`}>
                  {isConnected ? 'LIVE CONNECTED' : 'NOT CONNECTED (DEMO)'}
                </span>
              </div>
              <p className="text-xs dark:text-slate-400 text-slate-500">
                10-Microservice E-Commerce Architecture running on ports 9100–9110
              </p>
            </div>
          </div>
          <button
            onClick={closeConnectModal}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          
          {/* Status Alert Banner */}
          <div className={`p-4 rounded-2xl border flex items-start gap-4 ${
            isConnected
              ? 'dark:bg-emerald-500/10 bg-emerald-50/80 border-emerald-500/30 dark:border-emerald-500/20'
              : 'dark:bg-slate-800/40 bg-slate-100 border-slate-200 dark:border-slate-800'
          }`}>
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
              isConnected
                ? 'bg-emerald-500/20 text-emerald-500 dark:text-emerald-400'
                : 'bg-amber-500/20 text-amber-500 dark:text-amber-400'
            }`}>
              {isConnected ? <Radio className="w-5 h-5 animate-pulse" /> : <PowerOff className="w-5 h-5" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold dark:text-white text-slate-900">
                  {isConnected ? 'Telemetry Stream Active' : 'External Application Not Connected'}
                </h3>
                <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  RBAC: <strong className={isAdmin ? 'text-purple-600 dark:text-purple-400' : 'text-slate-400'}>{role}</strong>
                </span>
              </div>
              <p className="text-xs dark:text-slate-400 text-slate-600 mt-1 leading-relaxed">
                {isConnected
                  ? 'Synapse RiskOps is actively monitoring the 10 microservices. Real-time metric vectors (CPU, latency, error rate, connection pools) are being ingested, evaluated by the ML Engine, and mapped to the dependency topology.'
                  : 'The external e-commerce platform services are running independently, but are not connected to Synapse RiskOps. Click "Connect Application" below as an Admin to establish live monitoring.'}
              </p>
            </div>
          </div>

          {/* Feedback Messages */}
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Endpoints & Probe Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl border dark:border-white/5 border-slate-200 dark:bg-slate-950/40 bg-slate-50/50 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                  <Server className="w-4 h-4 text-cyan-500" /> API Gateway Endpoint
                </span>
                <span className="text-[10px] font-mono text-slate-400">Port 9101</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={gatewayUrl}
                  onChange={(e) => setGatewayUrl(e.target.value)}
                  className="flex-1 px-3 py-1.5 rounded-xl text-xs font-mono dark:bg-slate-900 bg-white border dark:border-white/10 border-slate-300 dark:text-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="http://localhost:9101"
                />
                <button
                  onClick={handleProbe}
                  disabled={probeStatus === 'probing'}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${probeStatus === 'probing' ? 'animate-spin' : ''}`} />
                  Probe
                </button>
              </div>
              {probeStatus === 'online' && (
                <span className="text-[11px] text-emerald-500 dark:text-emerald-400 flex items-center gap-1 font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Gateway reachable & responding 200 OK
                </span>
              )}
              {probeStatus === 'offline' && (
                <span className="text-[11px] text-rose-500 dark:text-rose-400 flex items-center gap-1 font-mono">
                  <AlertTriangle className="w-3.5 h-3.5" /> Gateway unreachable. Check if demo is started.
                </span>
              )}
            </div>

            <div className="p-4 rounded-2xl border dark:border-white/5 border-slate-200 dark:bg-slate-950/40 bg-slate-50/50 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold dark:text-white text-slate-900 flex items-center gap-2">
                  <ShoppingBag className="w-4 h-4 text-emerald-500" /> Storefront Customer Web App
                </span>
                <span className="text-[10px] font-mono text-slate-400">Port 9100</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono dark:text-slate-300 text-slate-700">{storefrontUrl}</span>
                <a
                  href={storefrontUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 transition-colors flex items-center gap-1.5 border border-cyan-500/30"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Open Website
                </a>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Interactive shopping workflow: catalog browsing, cart, checkout, payments, and chaos injection panel.
              </p>
            </div>
          </div>

          {/* Microservices Directory */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-black uppercase tracking-wider dark:text-slate-300 text-slate-700 flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-500" />
                Interconnected Microservices ({MICROSERVICES_LIST.length})
              </h4>
              <span className="text-[10px] font-mono text-slate-500">
                Independent processes communicating via HTTP/REST
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {MICROSERVICES_LIST.map((svc) => (
                <div
                  key={svc.name}
                  className="p-3 rounded-xl border dark:border-white/5 border-slate-200 dark:bg-slate-950/60 bg-white flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-400'}`} />
                    <div>
                      <div className="font-mono font-bold dark:text-white text-slate-900">{svc.name}</div>
                      <div className="text-[10px] text-slate-500 dark:text-slate-400">{svc.role}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      :{svc.port}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Footer Actions */}
        <div className="p-6 border-t dark:border-white/[0.06] border-slate-200 bg-slate-50/50 dark:bg-slate-950/40 flex items-center justify-between">
          <div>
            {!isAdmin ? (
              <span className="text-xs text-amber-500 dark:text-amber-400 flex items-center gap-1.5 font-medium">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                Admin role required to connect or disconnect services.
              </span>
            ) : (
              <span className="text-xs text-purple-600 dark:text-purple-400 flex items-center gap-1.5 font-medium">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                Authorized as Administrator ({role})
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={closeConnectModal}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
            >
              Close
            </button>

            {isConnected ? (
              <Button
                variant="danger"
                size="sm"
                onClick={handleDisconnect}
                disabled={!isAdmin || isSwitching}
                loading={isSwitching}
                className="flex items-center gap-2"
              >
                <PowerOff className="w-4 h-4" />
                Disconnect Website
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleConnect}
                disabled={!isAdmin || isSwitching}
                loading={isSwitching}
                className="flex items-center gap-2 shadow-glow-sm"
              >
                <Power className="w-4 h-4" />
                Connect All 10 Microservices
              </Button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
