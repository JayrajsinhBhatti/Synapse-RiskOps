import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

/**
 * Synapse RiskOps - React Entry Point
 * =====================================
 * Mounts the React application to the DOM.
 * StrictMode is enabled for development to catch common bugs.
 */
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
