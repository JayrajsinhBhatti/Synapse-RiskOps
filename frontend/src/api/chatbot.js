/**
 * frontend/src/api/chatbot.js
 *
 * Axios API client methods for chatbot communication:
 * - sendChatMessage(message, sessionId)
 * - getServiceHealth(serviceName)
 * - getSessionHistory(sessionId)
 * - clearSessionHistory(sessionId)
 */

import axios from 'axios';

// During dev, requests to /api/chatbot are proxied to genai-agent on port 8001
const CHATBOT_BASE_URL = import.meta.env.VITE_GENAI_AGENT_URL || '/api/chatbot';

const chatbotClient = axios.create({
  baseURL: CHATBOT_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

/**
 * Send a message to the SRE Chatbot.
 */
export async function sendChatMessage(message, sessionId = null) {
  const payload = { message };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  const response = await chatbotClient.post('/message', payload);
  return response.data;
}

/**
 * Query service health and risk score directly (Feature #1).
 */
export async function getServiceHealth(serviceName) {
  const response = await chatbotClient.get(`/health/${encodeURIComponent(serviceName)}`);
  return response.data;
}

/**
 * Retrieve list of monitored services.
 */
export async function getMonitoredServices() {
  const response = await chatbotClient.get('/services');
  return response.data;
}

/**
 * Get conversation history for a given session.
 */
export async function getSessionHistory(sessionId) {
  const response = await chatbotClient.get(`/history/${encodeURIComponent(sessionId)}`);
  return response.data;
}

/**
 * Reset conversation session memory.
 */
export async function clearSessionHistory(sessionId) {
  const response = await chatbotClient.delete(`/history/${encodeURIComponent(sessionId)}`);
  return response.data;
}

export default {
  sendChatMessage,
  getServiceHealth,
  getMonitoredServices,
  getSessionHistory,
  clearSessionHistory,
};
