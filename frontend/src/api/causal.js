/**
 * frontend/src/api/causal.js
 * API client for Chaos-Calibrated Causal Graph
 */

import apiClient from './client';

export async function fetchCausalGraph() {
  const res = await apiClient.get('/causal/graph');
  return res?.data !== undefined ? res.data : res;
}

export async function runCausalExperiment(payload) {
  const res = await apiClient.post('/causal/experiments/run', payload);
  return res?.data !== undefined ? res.data : res;
}

export async function fetchEdgeEvidence(source, target) {
  const res = await apiClient.get(`/causal/edges/${source}/${target}/evidence`);
  return res?.data !== undefined ? res.data : res;
}

export async function seedBaselineCalibrations() {
  const res = await apiClient.post('/causal/seed-baselines');
  return res?.data !== undefined ? res.data : res;
}

export async function fetchExperimentHistory(limit = 20) {
  const res = await apiClient.get('/causal/experiments/history', { params: { limit } });
  return res?.data !== undefined ? res.data : res;
}
