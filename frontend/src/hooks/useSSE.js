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
        if (eventName === 'incident_created' || eventName === 'incident_updated') {
          queryClient.invalidateQueries({ queryKey: ['incidents'] });
          queryClient.invalidateQueries({ queryKey: ['services'] });
          queryClient.invalidateQueries({ queryKey: ['topology'] });
          if (payload?.data?.id) {
            queryClient.invalidateQueries({ queryKey: ['incident', payload.data.id] });
            queryClient.invalidateQueries({ queryKey: ['incident-history', payload.data.id] });
          }
        } else if (eventName === 'risk_assessment') {
          queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
          queryClient.invalidateQueries({ queryKey: ['services'] });
          queryClient.invalidateQueries({ queryKey: ['topology'] });
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

    es.addEventListener('risk_assessment', (e) => {
      handleEvent('risk_assessment', e);
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
