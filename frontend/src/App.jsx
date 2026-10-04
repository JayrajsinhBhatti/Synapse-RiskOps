/**
 * frontend/src/App.jsx
 * 
 * Root Application Component.
 * Supports switching between the cinematic Landing Page and the Cyber-Ops Dashboard.
 */

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ChatbotProvider } from './context/ChatbotContext';
import DashboardLayout from './layouts/DashboardLayout';
import DashboardPage from './pages/DashboardPage';
import LandingPage from './pages/LandingPage';

// Configure React Query client with resilient defaults
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 15, // 15 seconds
      refetchOnWindowFocus: false,
      retry: 2,
    },
  },
});

export default function App() {
  const [activeView, setActiveView] = useState('landing');

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ChatbotProvider>
          {activeView === 'landing' ? (
            <LandingPage onLaunchApp={() => setActiveView('command-center')} />
          ) : (
            <DashboardLayout
              activeView={activeView}
              onViewChange={setActiveView}
            >
              <DashboardPage activeView={activeView} />
            </DashboardLayout>
          )}
        </ChatbotProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
