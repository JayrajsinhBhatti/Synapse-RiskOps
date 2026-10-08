/**
 * frontend/src/api/chaos.js
 * 
 * API client for the Chaos Experiment & Live Service Telemetry Proof Engine.
 * Supports:
 * - Real live service discovery (api-gateway, auth-service, order-service, payment-service, inventory-service, notification-svc)
 * - Live HTTP load generation (concurrency, RPS, duration, start/stop)
 * - Real Prometheus + Telemetry Bridge + ML Engine streaming telemetry
 * - Controlled chaos latency injection and recovery verification
 */

import apiClient from './client';

export async function getLiveServices() {
  return apiClient.get('/chaos/services');
}

export async function startServiceLoad({ serviceName, rps = 25, concurrency = 10, durationSeconds = 60 } = {}) {
  return apiClient.post('/chaos/load/start', {
    service_name: serviceName,
    rps,
    concurrency,
    duration_seconds: durationSeconds,
  });
}

export async function stopServiceLoad() {
  return apiClient.post('/chaos/load/stop');
}

export async function getLoadStatus() {
  return apiClient.get('/chaos/load/status');
}

export async function getLiveTelemetry(serviceName) {
  const params = serviceName ? { service_name: serviceName } : {};
  return apiClient.get('/chaos/telemetry/live', { params });
}

export async function injectChaos({ faultType = 'latency', intensity = 0.9, durationSeconds = 120, serviceName = 'payment-service' } = {}) {
  return apiClient.post('/chaos/inject', {
    fault_type: faultType,
    intensity,
    duration_seconds: durationSeconds,
    service_name: serviceName,
  });
}

export async function remediateChaos() {
  return apiClient.post('/chaos/remediate');
}

export async function resetChaos() {
  return apiClient.post('/chaos/reset');
}

export async function getChaosStatus() {
  return apiClient.get('/chaos/status');
}
