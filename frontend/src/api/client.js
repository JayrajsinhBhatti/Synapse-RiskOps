/**
 * frontend/src/api/client.js
 * Owner: Person 2 | Week: 6
 * 
 * Centralized Axios instance configured with base URL, JWT bearer token interceptor,
 * and robust error handling without auth-loop storms.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request Interceptor: Attach JWT Bearer Token if present
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('synapse_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Standardize error unwrapping and handle 401 gracefully
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const isLoginRequest = error.config?.url?.includes('/auth/login');
      const hadToken = !!localStorage.getItem('synapse_access_token');

      // Only dispatch unauthorized event if a previously authenticated session expired
      // Do NOT trigger when failing on the login form itself
      if (error.response.status === 401 && !isLoginRequest && hadToken) {
        localStorage.removeItem('synapse_access_token');
        localStorage.removeItem('synapse_user');
        window.dispatchEvent(new CustomEvent('synapse:unauthorized'));
      }

      const message =
        error.response.data?.detail ||
        error.response.data?.message ||
        `Request failed with status ${error.response.status}`;
      return Promise.reject(new Error(message));
    } else if (error.request) {
      return Promise.reject(
        new Error('Network error: Unable to reach Synapse RiskOps backend on port 8080.')
      );
    }
    return Promise.reject(error);
  }
);

export default apiClient;
