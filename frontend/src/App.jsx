/**
 * Synapse RiskOps - Root Application Component
 * ==============================================
 * Phase 1 placeholder. Full routing, auth context,
 * and React Query provider will be added in Phase 11.
 */
function App() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="glass-card p-12 text-center max-w-lg">
        {/* Logo / Brand */}
        <div className="mb-6">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-synapse-500 to-synapse-700 flex items-center justify-center mb-4 shadow-lg shadow-synapse-500/25">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold gradient-text">
            Synapse RiskOps
          </h1>
        </div>

        {/* Status */}
        <p className="text-gray-400 text-sm mb-6">
          Autonomous AI-Powered Risk Operations Pipeline
        </p>

        {/* Health Indicators */}
        <div className="space-y-3">
          <StatusRow label="Frontend" status="online" />
          <StatusRow label="Backend" status="pending" />
          <StatusRow label="ML Engine" status="pending" />
          <StatusRow label="Database" status="pending" />
        </div>

        <p className="text-gray-500 text-xs mt-8">
          Phase 1 — Project Setup Complete
        </p>
      </div>
    </div>
  );
}

/**
 * StatusRow Component
 * Shows the health status of each service.
 */
function StatusRow({ label, status }) {
  const statusConfig = {
    online:  { color: 'bg-emerald-500', text: 'Online',  textColor: 'text-emerald-400' },
    pending: { color: 'bg-amber-500',   text: 'Pending', textColor: 'text-amber-400'   },
    offline: { color: 'bg-red-500',     text: 'Offline', textColor: 'text-red-400'     },
  };

  const config = statusConfig[status] || statusConfig.pending;

  return (
    <div className="flex items-center justify-between py-2 px-4 rounded-lg bg-white/5">
      <span className="text-gray-300 text-sm font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${config.color} ${status === 'online' ? 'animate-pulse' : ''}`} />
        <span className={`text-xs font-medium ${config.textColor}`}>{config.text}</span>
      </div>
    </div>
  );
}

export default App;
