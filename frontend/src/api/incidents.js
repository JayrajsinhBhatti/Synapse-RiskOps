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
export async function updateIncidentStatus(incidentId, { status, comment, executed_actions = [] }) {
  return apiClient.patch(`/incidents/${incidentId}/status`, {
    status,
    comment,
    executed_actions,
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
