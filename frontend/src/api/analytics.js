/**
 * frontend/src/api/analytics.js
 * 
 * API client functions for Computed Reliability Metrics,
 * Multi-Metric Time Series, Change Events, Incident Ownership & Collaboration,
 * and Recovery Verification.
 */

import apiClient from './client';

// =====================================================
// Reliability Metrics & Analytics
// =====================================================

export async function getReliabilityMetrics() {
  return apiClient.get('/analytics/reliability');
}

export async function getServiceMetrics({ serviceId, serviceName, timeframe = '1h' } = {}) {
  const params = { timeframe };
  if (serviceId) params.service_id = serviceId;
  if (serviceName) params.service_name = serviceName;
  return apiClient.get('/analytics/metrics', { params });
}

export async function getChangeEvents({ serviceName } = {}) {
  const params = {};
  if (serviceName) params.service_name = serviceName;
  return apiClient.get('/analytics/change-events', { params });
}

// =====================================================
// Incident Ownership & Collaboration (P0)
// =====================================================

export async function acknowledgeIncident(incidentId) {
  return apiClient.post(`/incidents/${incidentId}/acknowledge`);
}

export async function assignIncident(incidentId, { assignedTo, note }) {
  return apiClient.post(`/incidents/${incidentId}/assign`, {
    assigned_to: assignedTo,
    note,
  });
}

export async function addIncidentNote(incidentId, { content }) {
  return apiClient.post(`/incidents/${incidentId}/notes`, { content });
}

export async function getIncidentNotes(incidentId) {
  return apiClient.get(`/incidents/${incidentId}/notes`);
}

// =====================================================
// Similar Incidents & Verification (P1)
// =====================================================

export async function getSimilarIncidents(incidentId) {
  return apiClient.get(`/incidents/${incidentId}/similar`);
}

export async function verifyRecovery(incidentId) {
  return apiClient.post(`/pipeline/verify-recovery/${incidentId}`);
}
