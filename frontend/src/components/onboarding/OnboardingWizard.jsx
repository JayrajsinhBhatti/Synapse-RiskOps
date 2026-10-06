import React, { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import {
  Building2,
  Server,
  Users,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Zap,
  Sparkles,
  ShieldCheck,
  Check,
  Sun,
  Moon,
  FastForward,
} from 'lucide-react';
import Button from '../common/Button';

export function OnboardingWizard({ onComplete }) {
  const { toggleTheme, isDark } = useTheme();
  const [step, setStep] = useState(1); // 1, 2, 3, or 'success'

  // Screen 1: Company State
  const [companyName, setCompanyName] = useState('Acme Cloud Services');
  const [industry, setIndustry] = useState('FinTech');
  const [companySize, setCompanySize] = useState('51-200');

  // Screen 2: Infrastructure State
  const [monitoredItems, setMonitoredItems] = useState([
    'Microservices',
    'Databases',
    'Kubernetes',
    'APIs',
  ]);
  const [primaryEnv, setPrimaryEnv] = useState('Production');

  // Screen 3: Operations State
  const [teamSize, setTeamSize] = useState('6-20');
  const [primaryFocus, setPrimaryFocus] = useState('Application reliability');
  const [currentTooling, setCurrentTooling] = useState([
    'Monitoring',
    'Logging',
    'Incident management',
  ]);

  const toggleItem = (list, setList, item) => {
    if (list.includes(item)) {
      setList(list.filter((x) => x !== item));
    } else {
      setList([...list, item]);
    }
  };

  const handleFinishOnboarding = () => {
    const config = {
      companyName,
      industry,
      companySize,
      monitoredItems,
      primaryEnv,
      teamSize,
      primaryFocus,
      currentTooling,
      completedAt: new Date().toISOString(),
    };
    localStorage.setItem('synapse_workspace_config', JSON.stringify(config));
    localStorage.setItem('synapse_onboarding_completed', 'true');
    setStep('success');
  };

  // Skip onboarding function: saves default config and proceeds directly
  const handleSkipOnboarding = () => {
    const config = {
      companyName: companyName || 'Production Cluster',
      industry: industry || 'Technology',
      companySize: companySize || '11-50',
      monitoredItems,
      primaryEnv,
      teamSize,
      primaryFocus,
      currentTooling,
      skipped: true,
      completedAt: new Date().toISOString(),
    };
    localStorage.setItem('synapse_workspace_config', JSON.stringify(config));
    localStorage.setItem('synapse_onboarding_completed', 'true');
    if (onComplete) onComplete();
  };

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
          <p className="text-xs dark:text-slate-300 text-slate-600 mt-3 leading-relaxed">
            We've tailored your dashboard for <strong className="dark:text-white text-slate-900">{companyName}</strong>.
            Let's see what's happening across your infrastructure right now.
          </p>

          <Button
            variant="cyan"
            size="lg"
            onClick={onComplete}
            iconRight={ArrowRight}
            className="w-full mt-8 font-bold text-xs"
          >
            Go to Operational Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen dark:bg-slate-950 bg-slate-100 flex flex-col justify-center py-12 px-6 selection:bg-indigo-500/30 transition-colors duration-300">
      {/* Background glow highlights */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-indigo-600/10 blur-[130px] rounded-full pointer-events-none" />

      <div className="max-w-2xl w-full mx-auto">
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
              <span className="text-[10px] block font-mono dark:text-slate-400 text-slate-500">Workspace Customization</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Quick Skip button in Header */}
            <button
              type="button"
              onClick={handleSkipOnboarding}
              className="text-xs font-semibold text-slate-500 hover:text-indigo-600 dark:hover:text-cyan-400 transition-colors px-3 py-1.5 rounded-lg border dark:border-slate-800 border-slate-200 dark:bg-slate-900 bg-white flex items-center gap-1.5 shadow-sm"
              title="Skip company setup and go directly to Dashboard"
            >
              <span>Skip Setup</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {/* Dark / Light Mode Toggle */}
            <button
              onClick={toggleTheme}
              title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle Theme"
              className="p-1.5 rounded-lg dark:text-slate-300 text-slate-600 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors flex items-center justify-center border dark:border-slate-800 border-slate-200 bg-white dark:bg-slate-900 shadow-sm"
            >
              {isDark ? (
                <Sun className="w-4 h-4 text-amber-300" />
              ) : (
                <Moon className="w-4 h-4 text-indigo-600" />
              )}
            </button>

            <div className="flex items-center gap-2 text-xs font-mono dark:text-slate-400 text-slate-500 dark:bg-slate-900 bg-white px-3 py-1.5 rounded-lg border dark:border-slate-800 border-slate-200 shadow-sm">
              <span>Step {step} of 3</span>
            </div>
          </div>
        </div>

        {/* Wizard Card Container */}
        <div className="dark:bg-slate-900/60 bg-white p-8 md:p-10 shadow-2xl dark:border-white/10 border-slate-200 rounded-3xl backdrop-blur-xl transition-colors duration-300">
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

              {/* High-Visibility Skip Option for Company Details */}
              <div className="p-4 rounded-2xl dark:bg-slate-950/80 bg-gradient-to-r from-indigo-50/90 via-cyan-50/60 to-white dark:from-slate-900 dark:to-slate-950 border dark:border-indigo-500/30 border-indigo-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-500 flex items-center justify-center text-white shadow-sm shrink-0">
                    <FastForward className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold dark:text-white text-slate-900 block">
                      Don't want to enter company details?
                    </span>
                    <span className="text-[11px] dark:text-slate-400 text-slate-600 block">
                      Skip directly into the live AIOps Dashboard with pre-configured defaults.
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleSkipOnboarding}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-md shadow-indigo-600/20 flex items-center justify-center gap-1.5 transition-all shrink-0 active:scale-95"
                >
                  <span>Skip & Open Dashboard</span>
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
                      Use default & skip to Step 2 &rarr;
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

              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
                {/* Prominent Direct Skip Button for Company Details */}
                <button
                  type="button"
                  onClick={handleSkipOnboarding}
                  className="w-full sm:w-auto text-xs font-bold dark:text-slate-300 text-slate-700 hover:text-indigo-600 dark:hover:text-cyan-400 transition-colors flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border dark:border-slate-700 border-slate-300 dark:bg-slate-950/60 bg-white hover:bg-slate-50 shadow-sm"
                  title="Skip company details and go straight to the operational dashboard"
                >
                  <FastForward className="w-4 h-4 text-indigo-500 dark:text-cyan-400" />
                  <span>Skip Company Details & Enter Dashboard</span>
                </button>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <Button
                    variant="cyan"
                    size="md"
                    onClick={() => setStep(2)}
                    iconRight={ArrowRight}
                    className="text-xs font-bold w-full sm:w-auto shadow-md shadow-cyan-500/10"
                  >
                    Continue to Infrastructure
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              SCREEN 2: INFRASTRUCTURE
             ======================================================== */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-600 dark:text-cyan-400 tracking-wider">
                  Phase 2 • Topology & Ingestion
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  Tell us about your infrastructure
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  Select the components you plan to monitor and govern through Synapse RiskOps.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-2">
                    What are you monitoring? <span className="dark:text-slate-500 text-slate-400 font-normal">(Select all that apply)</span>
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                      'Microservices',
                      'Cloud infrastructure',
                      'Databases',
                      'APIs',
                      'Kubernetes',
                      'Containers',
                      'Virtual machines',
                      'Other',
                    ].map((item) => {
                      const isChecked = monitoredItems.includes(item);
                      return (
                        <button
                          key={item}
                          type="button"
                          onClick={() => toggleItem(monitoredItems, setMonitoredItems, item)}
                          className={`p-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all ${
                            isChecked
                              ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                              : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                          }`}
                        >
                          <span className="truncate">{item}</span>
                          {isChecked && <Check className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0 ml-1" />}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-2">
                    What is your primary environment?
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {['Development', 'Staging', 'Production', 'Multi-environment'].map((env) => (
                      <button
                        key={env}
                        type="button"
                        onClick={() => setPrimaryEnv(env)}
                        className={`p-2.5 rounded-xl border text-xs font-medium transition-all text-center ${
                          primaryEnv === env
                            ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                            : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                        }`}
                      >
                        {env}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setStep(1)}
                  icon={ArrowLeft}
                  className="text-xs"
                >
                  Back
                </Button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSkipOnboarding}
                    className="text-xs font-semibold text-slate-500 hover:text-indigo-600 dark:hover:text-cyan-400 px-3 py-2 transition-colors"
                  >
                    Skip setup &rarr;
                  </button>
                  <Button
                    variant="cyan"
                    size="md"
                    onClick={() => setStep(3)}
                    iconRight={ArrowRight}
                    className="text-xs font-bold"
                  >
                    Continue
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================
              SCREEN 3: OPERATIONS
             ======================================================== */}
          {step === 3 && (
            <div className="space-y-6">
              <div>
                <span className="text-[10px] font-mono uppercase font-bold text-cyan-600 dark:text-cyan-400 tracking-wider">
                  Phase 3 • Incident Operations
                </span>
                <h2 className="text-xl font-extrabold dark:text-white text-slate-900 mt-1">
                  How does your team handle incidents?
                </h2>
                <p className="text-xs dark:text-slate-400 text-slate-600 mt-1">
                  Configure runbook automation triggers and on-call escalation routing.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-2">
                    On-call / SRE Team Size
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {['1-5', '6-20', '21-50', '50+'].map((sz) => (
                      <button
                        key={sz}
                        type="button"
                        onClick={() => setTeamSize(sz)}
                        className={`p-2.5 rounded-xl border text-xs font-medium transition-all text-center ${
                          teamSize === sz
                            ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                            : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                        }`}
                      >
                        {sz}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-2">
                    Primary Operational Focus
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {[
                      'Incident response',
                      'Infrastructure monitoring',
                      'Application reliability',
                      'Security operations',
                      'DevOps / SRE',
                    ].map((focus) => (
                      <button
                        key={focus}
                        type="button"
                        onClick={() => setPrimaryFocus(focus)}
                        className={`p-2.5 rounded-xl border text-xs font-medium text-left transition-all ${
                          primaryFocus === focus
                            ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                            : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                        }`}
                      >
                        {focus}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold dark:text-slate-300 text-slate-700 block mb-2">
                    Current Tooling Stack <span className="dark:text-slate-500 text-slate-400 font-normal">(Select all that apply)</span>
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {['Monitoring', 'Logging', 'Incident management', 'Automation'].map((tool) => {
                      const isChecked = currentTooling.includes(tool);
                      return (
                        <button
                          key={tool}
                          type="button"
                          onClick={() => toggleItem(currentTooling, setCurrentTooling, tool)}
                          className={`p-2 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all ${
                            isChecked
                              ? 'dark:bg-indigo-600/30 bg-indigo-50 dark:border-indigo-400 border-indigo-500 dark:text-white text-indigo-800 font-bold shadow-sm'
                              : 'dark:bg-slate-950/60 bg-white dark:border-slate-800 border-slate-200 dark:text-slate-400 text-slate-700 hover:bg-slate-50 hover:border-slate-300 dark:hover:text-white hover:text-slate-950 shadow-sm'
                          }`}
                        >
                          <span className="truncate">{tool}</span>
                          {isChecked && <Check className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0 ml-1" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="pt-5 border-t dark:border-white/5 border-slate-200 flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setStep(2)}
                  icon={ArrowLeft}
                  className="text-xs"
                >
                  Back
                </Button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSkipOnboarding}
                    className="text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-300 px-3 py-2"
                  >
                    Skip setup
                  </button>
                  <Button
                    variant="cyan"
                    size="md"
                    onClick={handleFinishOnboarding}
                    iconRight={Sparkles}
                    className="text-xs font-bold shadow-glow-cyan"
                  >
                    Create My Workspace
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default OnboardingWizard;
