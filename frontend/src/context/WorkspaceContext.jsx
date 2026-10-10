/**
 * frontend/src/context/WorkspaceContext.jsx
 * 
 * Centralized Operational Workspace Context.
 * Manages the global operational data mode:
 * - 'demo' (Explore with Demo Data / Simulation Dataset)
 * - 'connected' (Connect Your Services & Live Prometheus / Telemetry Bridge)
 * 
 * Ensures strict isolation between simulation data and production telemetry,
 * coordinates global cache invalidations, and powers the mode reconfiguration modal.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getSystemMode, setSystemMode, connectDemoApp } from '../api/system';


const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState(() => {
    return localStorage.getItem('synapse_operational_mode') || 'demo';
  });
  const [externalAppConnected, setExternalAppConnected] = useState(false);
  const [externalAppInfo, setExternalAppInfo] = useState(null);
  const [workspaceConfig, setWorkspaceConfig] = useState(() => {
    try {
      const saved = localStorage.getItem('synapse_workspace_config');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isModeModalOpen, setIsModeModalOpen] = useState(false);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);

  // Sync mode with backend on mount if authenticated
  useEffect(() => {
    const token = localStorage.getItem('synapse_access_token');
    if (!token) return;

    let isMounted = true;
    getSystemMode()
      .then((data) => {
        if (isMounted && data?.mode) {
          setMode(data.mode);
          setExternalAppConnected(Boolean(data.external_app_connected));
          setExternalAppInfo(data.external_app_info || null);
          localStorage.setItem('synapse_operational_mode', data.mode);
        }
      })
      .catch((err) => {
        console.debug('Failed to sync backend operational mode, using local state:', err);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Listen for custom event triggered by SSE system_mode_changed
  useEffect(() => {
    const handleModeChanged = (e) => {
      if (e.detail?.mode && e.detail.mode !== mode) {
        setMode(e.detail.mode);
        localStorage.setItem('synapse_operational_mode', e.detail.mode);
        getSystemMode().then((data) => {
          if (data) {
            setExternalAppConnected(Boolean(data.external_app_connected));
            setExternalAppInfo(data.external_app_info || null);
          }
        }).catch(() => {});
        queryClient.invalidateQueries();
      }
    };
    window.addEventListener('synapse:mode-changed', handleModeChanged);
    return () => window.removeEventListener('synapse:mode-changed', handleModeChanged);
  }, [mode, queryClient]);

  // Connect external demo microservices website (Admin action)
  const connectWebsite = useCallback(
    async (gatewayUrl = 'http://localhost:9101') => {
      setIsSwitching(true);
      try {
        const res = await connectDemoApp('connect', gatewayUrl);
        setMode('connected');
        setExternalAppConnected(true);
        setExternalAppInfo(res?.services ? { services: res.services, gateway_url: gatewayUrl } : null);
        localStorage.setItem('synapse_operational_mode', 'connected');
        queryClient.invalidateQueries();
        return res;
      } finally {
        setIsSwitching(false);
      }
    },
    [queryClient]
  );

  // Disconnect external demo microservices website (Admin action)
  const disconnectWebsite = useCallback(
    async () => {
      setIsSwitching(true);
      try {
        const res = await connectDemoApp('disconnect');
        setMode('demo');
        setExternalAppConnected(false);
        setExternalAppInfo(null);
        localStorage.setItem('synapse_operational_mode', 'demo');
        queryClient.invalidateQueries();
        return res;
      } finally {
        setIsSwitching(false);
      }
    },
    [queryClient]
  );

  // Switch mode action
  const switchMode = useCallback(
    async (newMode, config = {}) => {
      setIsSwitching(true);
      try {
        const payload = {
          mode: newMode,
          connection_type: config.connection_type || 'prometheus_bridge',
          endpoint_url: config.endpoint_url || 'http://localhost:9090',
          verified: newMode === 'connected',
        };

        const res = await setSystemMode(payload);
        const actualMode = res?.mode || newMode;

        setMode(actualMode);
        localStorage.setItem('synapse_operational_mode', actualMode);

        const updatedConfig = {
          ...(workspaceConfig || {}),
          operationalMode: actualMode,
          connectionType: payload.connection_type,
          endpointUrl: payload.endpoint_url,
          lastSwitchedAt: new Date().toISOString(),
        };
        localStorage.setItem('synapse_workspace_config', JSON.stringify(updatedConfig));
        setWorkspaceConfig(updatedConfig);

        queryClient.invalidateQueries();
        setIsModeModalOpen(false);
        return res;
      } finally {
        setIsSwitching(false);
      }
    },
    [workspaceConfig, queryClient]
  );

  const value = {
    mode,
    isDemoMode: mode === 'demo',
    isConnectedMode: mode === 'connected',
    externalAppConnected,
    externalAppInfo,
    workspaceConfig,
    isSwitching,
    switchMode,
    isModeModalOpen,
    openModeModal: () => setIsModeModalOpen(true),
    closeModeModal: () => setIsModeModalOpen(false),
    isConnectModalOpen,
    openConnectModal: () => setIsConnectModalOpen(true),
    closeConnectModal: () => setIsConnectModalOpen(false),
    connectWebsite,
    disconnectWebsite,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}

