/**
 * frontend/src/api/dry_run.js
 * 
 * API client helper functions for Dry-Run Twin (Counterfactual Remediation):
 * - simulateDryRun({ serviceName, incidentId, candidateActions, environment, currentMetrics })
 * - getDryRunHistory(limit, serviceName)
 * - getDryRunDetail(simulationId)
 * - executeDryRunAction({ simulationId, selectedAction, approvalNotes })
 */

import apiClient from './client';

export const simulateDryRun = async ({
  serviceName,
  incidentId = null,
  candidateActions = null,
  environment = 'production',
  currentMetrics = null,
}) => {
  return apiClient.post('/dry-run/simulate', {
    service_name: serviceName,
    incident_id: incidentId || undefined,
    candidate_actions: candidateActions && candidateActions.length > 0 ? candidateActions : undefined,
    environment,
    current_metrics: currentMetrics || undefined,
  });
};

export const getDryRunHistory = async (limit = 25, serviceName = null) => {
  const params = { limit };
  if (serviceName) params.service_name = serviceName;
  return apiClient.get('/dry-run/history', { params });
};

export const getDryRunDetail = async (simulationId) => {
  return apiClient.get(`/dry-run/${simulationId}`);
};

export const executeDryRunAction = async ({ simulationId, selectedAction = null, approvalNotes = '' }) => {
  return apiClient.post(`/dry-run/${simulationId}/execute`, {
    selected_action: selectedAction || undefined,
    approval_notes: approvalNotes || undefined,
  });
};
