/**
 * frontend/src/hooks/useSSE.js
 * Owner: Person 2 | Week: 6
 * 
 * Server-Sent Events (SSE) hook connecting to backend /api/incidents/stream.
 * Dispatches real-time events, manages connection lifecycle with automatic reconnect,
 * and triggers TanStack Query cache invalidations so the dashboard stays live.
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useSSE() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('connecting'); // 'connected' | 'connecting' | 'disconnected'
  const [lastEvent, setLastEvent] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const streamUrl = '/api/incidents/stream';
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;
    setStatus('connecting');

    es.onopen = () => {
      setStatus('connected');
    };

    es.onerror = () => {
      setStatus('disconnected');
      es.close();
      // Retry in 5 seconds
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 5000);
    };

    const handleEvent = (eventName, evt) => {
      try {
        const payload = JSON.parse(evt.data);
        const eventItem = {
          name: eventName,
          payload,
          timestamp: new Date().toISOString(),
        };

        setLastEvent(eventItem);
        setRecentEvents((prev) => [eventItem, ...prev.slice(0, 49)]);

        // Intelligent React Query Cache Invalidation
        if (eventName === 'incident_created' || eventName === 'incident_updated' || eventName === 'incident_deleted') {
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
          queryClient.invalidateQueries({ queryKey: ['services'] });
          queryClient.invalidateQueries({ queryKey: ['topology'] });
          queryClient.invalidateQueries({ queryKey: ['analytics'] });
          if (payload?.data?.id) {
            queryClient.invalidateQueries({ queryKey: ['incident', payload.data.id] });
            queryClient.invalidateQueries({ queryKey: ['incident-history', payload.data.id] });
          }
        } else if (eventName === 'risk_alert' || eventName === 'risk_assessment') {
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
          queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
          queryClient.invalidateQueries({ queryKey: ['services'] });
          queryClient.invalidateQueries({ queryKey: ['topology'] });
          queryClient.invalidateQueries({ queryKey: ['analytics'] });
        } else if (eventName === 'system_mode_changed') {
          queryClient.invalidateQueries();
          if (payload?.mode) {
            localStorage.setItem('synapse_operational_mode', payload.mode);
            window.dispatchEvent(new CustomEvent('synapse:mode-changed', { detail: payload }));
          }
        } else if (
          eventName === 'retention_purged' ||
          eventName === 'incidents_bulk_deleted' ||
          eventName === 'risk_assessments_bulk_deleted' ||
          eventName === 'risk_assessment_deleted' ||
          eventName === 'incident_history_deleted'
        ) {
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
          queryClient.invalidateQueries({ queryKey: ['risk-assessments'] });
          queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
          queryClient.invalidateQueries({ queryKey: ['analytics'] });
        }
      } catch (err) {
        console.warn(`Error parsing SSE ${eventName} event:`, err);
      }
    };

    es.addEventListener('connected', (e) => {
      setStatus('connected');
      handleEvent('connected', e);
    });

    es.addEventListener('heartbeat', (e) => {
      setStatus('connected');
      handleEvent('heartbeat', e);
    });

    es.addEventListener('incident_created', (e) => {
      handleEvent('incident_created', e);
    });

    es.addEventListener('incident_updated', (e) => {
      handleEvent('incident_updated', e);
    });

    es.addEventListener('incident_deleted', (e) => {
      handleEvent('incident_deleted', e);
    });

    es.addEventListener('risk_alert', (e) => {
      handleEvent('risk_alert', e);
    });

    es.addEventListener('risk_assessment', (e) => {
      handleEvent('risk_assessment', e);
    });

    es.addEventListener('system_mode_changed', (e) => {
      handleEvent('system_mode_changed', e);
    });

    es.addEventListener('retention_purged', (e) => {
      handleEvent('retention_purged', e);
    });

    es.addEventListener('incidents_bulk_deleted', (e) => {
      handleEvent('incidents_bulk_deleted', e);
    });

    es.addEventListener('risk_assessments_bulk_deleted', (e) => {
      handleEvent('risk_assessments_bulk_deleted', e);
    });

    es.addEventListener('risk_assessment_deleted', (e) => {
      handleEvent('risk_assessment_deleted', e);
    });

    es.addEventListener('incident_history_deleted', (e) => {
      handleEvent('incident_history_deleted', e);
    });
  }, [queryClient]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);

  return {
    status,
    isConnected: status === 'connected',
    lastEvent,
    recentEvents,
    reconnect: connect,
  };
}
