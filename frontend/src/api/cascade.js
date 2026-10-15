/**
 * frontend/src/api/cascade.js
 * 
 * API client functions for Cascade Interception Planner:
 * - simulateCascade(seedService, failureType, severity)
 * - getInterceptionPlans(seedService, failureType)
 * - executeInterceptionPlan(planId, seedService, strategy, approvalNotes, incidentId)
 */

import apiClient from './client';

export const simulateCascade = async ({ seedService, failureType = 'latency_spike', severity = 0.85, activeIncidentId = null }) => {
  return apiClient.post('/cascade/simulate', {
    seed_service: seedService,
    failure_type: failureType,
    severity: Number(severity),
    active_incident_id: activeIncidentId,
  });
};

export const getInterceptionPlans = async (seedService, failureType = 'latency_spike') => {
  return apiClient.get('/cascade/plans', {
    params: { seed_service: seedService, failure_type: failureType },
  });
};

export const executeInterceptionPlan = async ({ planId, seedService, strategy, approvalNotes = '', incidentId = null }) => {
  return apiClient.post('/cascade/execute-plan', {
    plan_id: planId,
    seed_service: seedService,
    strategy: strategy,
    approval_notes: approvalNotes,
    incident_id: incidentId,
  });
};
