/**
 * frontend/src/App.jsx
 * 
 * Root Application Component.
 * Implements the full SaaS product flow:
 *   Landing → Auth → Onboarding → Command Center Dashboard
 * 
 * Uses AuthContext for JWT authentication state and localStorage
 * for onboarding completion persistence.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ChatbotProvider } from './context/ChatbotContext';
import DashboardLayout from './layouts/DashboardLayout';
import DashboardPage from './pages/DashboardPage';
import LandingPage from './pages/LandingPage';
import { AuthScreen } from './components/auth/AuthScreen';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';

// Configure React Query client with resilient defaults
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 15,
      refetchOnWindowFocus: false,
      retry: 2,
    },
  },
});

/**
 * AppRouter — the inner shell that has access to AuthContext.
 * Manages the screen flow: landing → auth → onboarding → dashboard.
 */
function AppRouter() {
  const { isAuthenticated, isLoading, logout } = useAuth();

  // Determine initial view based on existing auth & onboarding state
  const [view, setView] = useState(() => {
    const token = localStorage.getItem('synapse_access_token');
    const onboarded = localStorage.getItem('synapse_onboarding_completed');
    if (token && onboarded === 'true') return 'dashboard';
    if (token) return 'onboarding';
    return 'landing';
  });

  // Transition CSS for smooth screen switching
  const [isTransitioning, setIsTransitioning] = useState(false);

  const transitionTo = useCallback((nextView) => {
    setIsTransitioning(true);
    setTimeout(() => {
      setView(nextView);
      setTimeout(() => setIsTransitioning(false), 50);
    }, 300);
  }, []);

  // Sync view when auth state changes (e.g., logout)
  useEffect(() => {
    if (!isLoading && !isAuthenticated && view !== 'landing' && view !== 'auth') {
      setView('landing');
    }
  }, [isAuthenticated, isLoading, view]);

  // Handle logout override: go back to landing
  const handleLogout = useCallback(() => {
    logout();
    localStorage.removeItem('synapse_onboarding_completed');
    localStorage.removeItem('synapse_workspace_config');
    transitionTo('landing');
  }, [logout, transitionTo]);

  // Auth loading spinner
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-cyan-400 flex items-center justify-center animate-pulse">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span className="text-xs font-mono text-slate-400 animate-pulse">Initializing Synapse RiskOps...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`transition-opacity duration-300 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
      {/* SCREEN: LANDING PAGE */}
      {view === 'landing' && (
        <LandingPage
          onLaunchApp={() => transitionTo('auth')}
          onSignIn={() => transitionTo('auth')}
          onGetStarted={() => transitionTo('auth')}
        />
      )}

      {/* SCREEN: AUTHENTICATION */}
      {view === 'auth' && (
        <AuthScreen
          onAuthSuccess={() => {
            const onboarded = localStorage.getItem('synapse_onboarding_completed');
            if (onboarded === 'true') {
              transitionTo('dashboard');
            } else {
              transitionTo('onboarding');
            }
          }}
          onBackToLanding={() => transitionTo('landing')}
        />
      )}

      {/* SCREEN: ONBOARDING WIZARD */}
      {view === 'onboarding' && (
        <OnboardingWizard
          onComplete={() => transitionTo('dashboard')}
        />
      )}

      {/* SCREEN: OPERATIONAL DASHBOARD */}
      {!['landing', 'auth', 'onboarding'].includes(view) && (
        <DashboardLayout
          activeView={view === 'dashboard' ? 'command-center' : view}
          onViewChange={(v) => setView(v)}
          onLogout={handleLogout}
        >
          <DashboardPage
            activeView={view === 'dashboard' ? 'command-center' : view}
            onViewChange={(v) => setView(v)}
          />
        </DashboardLayout>
      )}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <ChatbotProvider>
            <AppRouter />
          </ChatbotProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
