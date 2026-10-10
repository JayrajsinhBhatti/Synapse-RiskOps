/**
 * frontend/src/api/system.js
 * 
 * API client functions for Operational Mode management, Connection Verification,
 * and Time-based Data Retention policies.
 */

import apiClient from './client';

// =====================================================
// Operational Data Mode Operations
// =====================================================

/**
 * Fetch the active operational data mode ('demo' or 'connected') and configuration.
 */
export async function getSystemMode() {
  return apiClient.get('/system/mode');
}

/**
 * Update the active operational data mode and optional connection settings.
 * @param {Object} payload { mode: 'demo' | 'connected', connection_type, endpoint_url, verified }
 */
export async function setSystemMode(payload) {
  return apiClient.post('/system/mode', payload);
}

/**
 * Verify live connection to Prometheus, telemetry bridge, and microservices.
 * @param {Object} payload { connection_method, prometheus_url, auth_type, auth_token, auth_username, auth_password, backfill_hours, target_services }
 */
export async function verifyConnection(payload) {
  return apiClient.post('/system/verify-connection', payload);
}

/**
 * Admin connect/disconnect of external 10-microservice demo application.
 * @param {'connect' | 'disconnect'} action
 * @param {string} gatewayUrl
 */
export async function connectDemoApp(action = 'connect', gatewayUrl = 'http://localhost:9101') {
  return apiClient.post('/system/connect-demo-app', { action, gateway_url: gatewayUrl });
}


/**
 * Retrieve previous 24–48 hours of metrics from Prometheus to solve ML cold-start.
 * @param {Object} payload { hours: 24 | 48, prometheus_url, auth_type, auth_token, services }
 */
export async function backfillMetrics(payload) {
  return apiClient.post('/system/backfill', payload);
}

/**
 * Ingest telemetry metrics via universal REST API (POST /api/v1/ingest/metrics).
 * @param {Object} payload { service_name, cpu_usage, memory_usage, error_rate, response_time_p99, network_latency_ms, request_count }
 */
export async function ingestMetric(payload) {
  return apiClient.post('/v1/ingest/metrics', payload);
}

/**
 * Batch configure detected services during onboarding (rename, criticality, is_active).
 * @param {Array} services [{ id, service_name, display_name, criticality, is_active, dependencies }]
 */
export async function batchConfigureServices(services) {
  return apiClient.post('/services/batch-configure', { services });
}

// =====================================================
// Time-based Retention Policy Operations
// =====================================================

/**
 * Fetch current retention policies for incidents and risk assessments.
 */
export async function getRetentionSettings() {
  return apiClient.get('/retention/settings');
}

/**
 * Update retention policy (e.g. '1d', '7d', '30d', '90d', 'all').
 * Automatically triggers background prune of records older than the selected retention window.
 * @param {Object} payload { incidents_policy?, risk_assessments_policy? }
 */
export async function updateRetentionSettings(payload) {
  return apiClient.put('/retention/settings', payload);
}

/**
 * Manually trigger retention policy prune for a specific module or all modules.
 * @param {string} module 'all' | 'incidents' | 'risk_assessments'
 */
export async function triggerRetentionPurge(module = 'all') {
  return apiClient.post('/retention/purge', { module });
}
