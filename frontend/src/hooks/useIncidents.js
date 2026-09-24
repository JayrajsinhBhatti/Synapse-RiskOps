/**
 * frontend/src/hooks/useIncidents.js
 * Owner: Person 2 | Week: 6
 * 
 * TanStack React Query hooks for fetching, caching, and mutating incidents,
 * microservice topology, risk assessments, and pipeline remediation.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getIncidents,
  getIncidentById,
  getIncidentHistory,
  updateIncidentStatus,
  getServices,
  getServiceTopology,
  getLatestRiskAssessments,
  getRiskAssessments,
  diagnoseAndRoute,
  executeRemediation,
  triggerAlert,
} from '../api/incidents';

function hasAuthToken() {
  return !!localStorage.getItem('synapse_access_token');
}

/**
 * Hook to fetch filtered incident list.
 */
export function useIncidents(filters = {}) {
  return useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => getIncidents(filters),
    enabled: hasAuthToken(),
    staleTime: 10000,
  });
}

/**
 * Hook to fetch a single incident with full details.
 */
export function useIncident(incidentId) {
  return useQuery({
    queryKey: ['incident', incidentId],
    queryFn: () => getIncidentById(incidentId),
    enabled: hasAuthToken() && !!incidentId,
  });
}

/**
 * Hook to fetch chronological history of an incident.
 */
export function useIncidentHistory(incidentId) {
  return useQuery({
    queryKey: ['incident-history', incidentId],
    queryFn: () => getIncidentHistory(incidentId),
    enabled: hasAuthToken() && !!incidentId,
  });
}

/**
 * Hook to fetch all microservices.
 */
export function useServices() {
  return useQuery({
    queryKey: ['services'],
    queryFn: () => getServices(),
    enabled: hasAuthToken(),
    staleTime: 30000,
  });
}

/**
 * Hook to fetch service dependency topology graph.
 */
export function useTopology() {
  return useQuery({
    queryKey: ['topology'],
    queryFn: () => getServiceTopology(),
    enabled: hasAuthToken(),
    staleTime: 30000,
  });
}

/**
 * Hook to fetch latest risk assessments across all services.
 */
export function useLatestRisk() {
  return useQuery({
    queryKey: ['latest-risk'],
    queryFn: () => getLatestRiskAssessments(),
    enabled: hasAuthToken(),
    staleTime: 15000,
  });
}

/**
 * Hook to mutate/update incident status.
 */
export function useUpdateIncidentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ incidentId, status, comment, executed_actions }) =>
      updateIncidentStatus(incidentId, { status, comment, executed_actions }),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', variables.incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-history', variables.incidentId] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
}

/**
 * Hook to trigger automated remediation via backend orchestrator.
 */
export function useExecuteRemediation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => executeRemediation(payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['topology'] });
      if (variables.incident_id) {
        queryClient.invalidateQueries({ queryKey: ['incident', variables.incident_id] });
        queryClient.invalidateQueries({ queryKey: ['incident-history', variables.incident_id] });
      }
    },
  });
}

/**
 * Hook to trigger alert injection.
 */
export function useTriggerAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => triggerAlert(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['topology'] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
    },
  });
}

/**
 * Hook to trigger AI diagnosis & confidence routing.
 */
export function useDiagnoseAndRoute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => diagnoseAndRoute(payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      if (variables.incident_id) {
        queryClient.invalidateQueries({ queryKey: ['incident', variables.incident_id] });
      }
    },
  });
}
