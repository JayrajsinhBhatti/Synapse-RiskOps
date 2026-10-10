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
  deleteIncident,
  deleteIncidentHistory,
  deleteAllIncidents,
  deleteRiskAssessment,
  deleteAllRiskAssessments,
} from '../api/incidents';
import {
  getRetentionSettings,
  updateRetentionSettings,
  triggerRetentionPurge,
  getSystemMode,
  setSystemMode,
} from '../api/system';

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
    staleTime: 4000,
    refetchInterval: 4000,
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
    staleTime: 15000,
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
    staleTime: 15000,
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
    staleTime: 4000,
    refetchInterval: 4000,
  });
}

/**
 * Hook to fetch historical risk assessment records.
 */
export function useRiskAssessments(params = {}) {
  return useQuery({
    queryKey: ['risk-assessments', params],
    queryFn: () => getRiskAssessments(params),
    enabled: hasAuthToken(),
    staleTime: 30000,
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

// =====================================================
// Deletion Operations (Individual & Bulk)
// =====================================================

/**
 * Hook to delete an individual incident.
 */
export function useDeleteIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (incidentId) => deleteIncident(incidentId),
    onSuccess: (data, incidentId) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.removeQueries({ queryKey: ['incident', incidentId] });
      queryClient.removeQueries({ queryKey: ['incident-history', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
}

/**
 * Hook to delete an individual audit history entry.
 */
export function useDeleteIncidentHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ historyId }) => deleteIncidentHistory(historyId),
    onSuccess: (data, variables) => {
      if (variables.incidentId) {
        queryClient.invalidateQueries({ queryKey: ['incident-history', variables.incidentId] });
        queryClient.invalidateQueries({ queryKey: ['incident', variables.incidentId] });
      }
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
}

/**
 * Hook to delete all incidents for the active data mode.
 */
export function useDeleteAllIncidents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mode) => deleteAllIncidents(mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident'] });
      queryClient.invalidateQueries({ queryKey: ['incident-history'] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
}

/**
 * Hook to delete an individual risk assessment record.
 */
export function useDeleteRiskAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assessmentId) => deleteRiskAssessment(assessmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk-assessments'] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
    },
  });
}

/**
 * Hook to delete all risk assessments for the active data mode.
 */
export function useDeleteAllRiskAssessments() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mode) => deleteAllRiskAssessments(mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk-assessments'] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
    },
  });
}

// =====================================================
// Retention Policy Operations
// =====================================================

/**
 * Hook to fetch retention settings.
 */
export function useRetentionSettings() {
  return useQuery({
    queryKey: ['retention-settings'],
    queryFn: () => getRetentionSettings(),
    enabled: hasAuthToken(),
    staleTime: 30000,
  });
}

/**
 * Hook to update retention settings and trigger time-based pruning.
 */
export function useUpdateRetentionSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateRetentionSettings(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['retention-settings'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments'] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
    },
  });
}

/**
 * Hook to manually trigger a retention policy prune.
 */
export function useTriggerRetentionPurge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (module) => triggerRetentionPurge(module),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessments'] });
      queryClient.invalidateQueries({ queryKey: ['latest-risk'] });
    },
  });
}

// =====================================================
// Operational Data Mode Operations
// =====================================================

/**
 * Hook to fetch current system mode.
 */
export function useSystemMode() {
  return useQuery({
    queryKey: ['system-mode'],
    queryFn: () => getSystemMode(),
    enabled: hasAuthToken(),
    staleTime: 30000,
  });
}

/**
 * Hook to switch operational data mode.
 */
export function useSetSystemMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => setSystemMode(payload),
    onSuccess: (data) => {
      if (data?.mode) {
        localStorage.setItem('synapse_operational_mode', data.mode);
      }
      queryClient.invalidateQueries();
    },
  });
}

