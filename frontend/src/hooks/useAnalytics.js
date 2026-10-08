/**
 * frontend/src/hooks/useAnalytics.js
 * 
 * React Query hooks for computed reliability metrics, time-series telemetry,
 * change events, incident ownership, notes, and recovery verification.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getReliabilityMetrics,
  getServiceMetrics,
  getChangeEvents,
  getSimilarIncidents,
  getIncidentNotes,
  acknowledgeIncident,
  assignIncident,
  addIncidentNote,
  verifyRecovery,
} from '../api/analytics';

export function useReliabilityMetrics() {
  return useQuery({
    queryKey: ['analytics', 'reliability'],
    queryFn: getReliabilityMetrics,
    refetchInterval: 15000, // Poll every 15s to update real computed KPIs
    staleTime: 10000,
  });
}

export function useServiceMetrics({ serviceId, serviceName, timeframe = '1h' }) {
  return useQuery({
    queryKey: ['analytics', 'metrics', serviceId || serviceName, timeframe],
    queryFn: () => getServiceMetrics({ serviceId, serviceName, timeframe }),
    enabled: Boolean(serviceId || serviceName),
    refetchInterval: 10000, // Update telemetry points
    staleTime: 5000,
  });
}

export function useChangeEvents({ serviceName } = {}) {
  return useQuery({
    queryKey: ['analytics', 'change-events', serviceName],
    queryFn: () => getChangeEvents({ serviceName }),
    staleTime: 30000,
  });
}

export function useSimilarIncidents(incidentId) {
  return useQuery({
    queryKey: ['incidents', incidentId, 'similar'],
    queryFn: () => getSimilarIncidents(incidentId),
    enabled: Boolean(incidentId),
    staleTime: 30000,
  });
}

export function useIncidentNotes(incidentId) {
  return useQuery({
    queryKey: ['incidents', incidentId, 'notes'],
    queryFn: () => getIncidentNotes(incidentId),
    enabled: Boolean(incidentId),
    refetchInterval: 8000,
  });
}

export function useAcknowledgeIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (incidentId) => acknowledgeIncident(incidentId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'reliability'] });
    },
  });
}

export function useAssignIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ incidentId, assignedTo, note }) =>
      assignIncident(incidentId, { assignedTo, note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

export function useAddIncidentNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ incidentId, content }) => addIncidentNote(incidentId, { content }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incidents', variables.incidentId, 'notes'] });
      queryClient.invalidateQueries({ queryKey: ['incidents', variables.incidentId, 'history'] });
    },
  });
}

export function useVerifyRecovery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (incidentId) => verifyRecovery(incidentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'reliability'] });
    },
  });
}
