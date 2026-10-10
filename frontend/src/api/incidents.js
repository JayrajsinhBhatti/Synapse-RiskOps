/**
 * frontend/src/api/incidents.js
 * Owner: Person 2 | Week: 6
 * 
 * API client functions for Incidents, Service Topology, Risk Assessments,
 * Authentication, and Orchestration Pipeline.
 */

import apiClient from './client';

// =====================================================
// Incident Operations
// =====================================================

/**
 * Fetch all incidents with optional filtering.
 */
export async function getIncidents(params = {}) {
  return apiClient.get('/incidents', { params });
}

/**
 * Fetch a single incident by ID (includes audit trail history).
 */
export async function getIncidentById(incidentId) {
  return apiClient.get(`/incidents/${incidentId}`);
}

/**
 * Update the status of an incident (open, investigating, mitigated, resolved).
 */
export async function updateIncidentStatus(incidentId, { status }) {
  return apiClient.patch(`/incidents/${incidentId}`, {
    status,
  });
}

/**
 * Fetch chronological audit history of an incident.
 */
export async function getIncidentHistory(incidentId) {
  return apiClient.get(`/incidents/${incidentId}/history`);
}

/**
 * Inject a new incident alert into the system.
 */
export async function triggerAlert(alertData) {
  return apiClient.post('/incidents/alert', alertData);
}

/**
 * Delete a specific incident by ID.
 */
export async function deleteIncident(incidentId) {
  return apiClient.delete(`/incidents/${incidentId}`);
}

/**
 * Delete a specific audit history entry by ID.
 */
export async function deleteIncidentHistory(historyId) {
  return apiClient.delete(`/incidents/history/${historyId}`);
}

/**
 * Delete all incidents for the active data mode (requires confirm_all=true).
 */
export async function deleteAllIncidents(mode) {
  const params = { confirm_all: true };
  if (mode) params.mode = mode;
  return apiClient.delete('/incidents', { params });
}

// =====================================================
// Services & Topology Operations
// =====================================================

/**
 * Fetch list of all registered microservices.
 */
export async function getServices() {
  return apiClient.get('/services');
}

/**
 * Fetch the complete microservice dependency graph topology.
 */
export async function getServiceTopology() {
  return apiClient.get('/services/topology');
}

// =====================================================
// Risk Assessment Operations
// =====================================================

/**
 * Fetch the latest risk assessment score for all services.
 */
export async function getLatestRiskAssessments() {
  return apiClient.get('/risk-assessments/latest');
}

/**
 * Fetch historical risk assessments.
 */
export async function getRiskAssessments(params = {}) {
  return apiClient.get('/risk-assessments', { params });
}

/**
 * Delete an individual risk assessment record by ID.
 */
export async function deleteRiskAssessment(assessmentId) {
  return apiClient.delete(`/risk-assessments/${assessmentId}`);
}

/**
 * Delete all risk assessments for the active data mode (requires confirm_all=true).
 */
export async function deleteAllRiskAssessments(mode) {
  const params = { confirm_all: true };
  if (mode) params.mode = mode;
  return apiClient.delete('/risk-assessments', { params });
}

// =====================================================
// Orchestration & Remediation Pipeline
// =====================================================

/**
 * Trigger diagnosis and confidence routing pipeline for an incident.
 */
export async function diagnoseAndRoute(payload) {
  return apiClient.post('/pipeline/diagnose-and-route', payload);
}

/**
 * Execute remediation playbook for an incident.
 */
export async function executeRemediation(payload) {
  return apiClient.post('/pipeline/remediate', payload);
}

// =====================================================
// Authentication Operations
// =====================================================

/**
 * Authenticate with username and password.
 */
export async function loginUser(username, password) {
  return apiClient.post('/auth/login', { username, password });
}

/**
 * Get profile of current logged-in user.
 */
export async function getCurrentUser() {
  return apiClient.get('/auth/me');
}
