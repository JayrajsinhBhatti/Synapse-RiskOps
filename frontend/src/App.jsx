/**
 * frontend/src/App.jsx
 * Owner: Person 2 | Week: 6
 * 
 * Root Application Component.
 * Configures TanStack React Query, AuthProvider, ChatbotProvider,
 * and mounts the Cyber-Ops DashboardLayout and DashboardPage.
 */

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ChatbotProvider } from './context/ChatbotContext';
import DashboardLayout from './layouts/DashboardLayout';
import DashboardPage from './pages/DashboardPage';

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
  const [activeView, setActiveView] = useState('command-center');

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ChatbotProvider>
          <DashboardLayout
            activeView={activeView}
            onViewChange={setActiveView}
          >
            <DashboardPage activeView={activeView} />
          </DashboardLayout>
        </ChatbotProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
