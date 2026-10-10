/**
 * frontend/src/components/common/NotificationPreferencesModal.jsx
 * 
 * Notification Preferences & Integrations Hub.
 * Implements UX Weakness #8 & Gap #12.
 * Configures Slack webhook, PagerDuty, Email, and n8n webhook notifications.
 */

import React, { useState } from 'react';
import {
  Bell,
  CheckCircle2,
  X,
  MessageSquare,
  Radio,
  Mail,
  Zap,
  Save,
} from 'lucide-react';

export default function NotificationPreferencesModal({ isOpen, onClose }) {
  const [channels, setChannels] = useState(() => {
    const saved = localStorage.getItem('synapse_notification_prefs');
    return saved
      ? JSON.parse(saved)
      : {
          slack: { enabled: true, webhook: 'https://hooks.slack.com/services/T00/B00/X00', minSeverity: 'HIGH' },
          pagerduty: { enabled: true, integrationKey: 'pd-live-key-4912903', minSeverity: 'CRITICAL' },
          email: { enabled: true, recipients: 'jayrajsinhbhatti9687@gmail.com', minSeverity: 'HIGH' },
          n8n: { enabled: true, webhookUrl: 'http://localhost:5678/webhook/synapse-risk', minSeverity: 'ALL' },
        };
  });

  const [savedSuccess, setSavedSuccess] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);
  const [testEmailResult, setTestEmailResult] = useState(null);

  const handleTestEmail = async () => {
    setTestingEmail(true);
    setTestEmailResult(null);
    try {
      const token = localStorage.getItem('access_token');
      const targetRecipient = channels.email?.recipients || 'jayrajsinhbhatti9687@gmail.com';
      const res = await fetch('/api/system/test-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ recipient: targetRecipient }),
      });
      const data = await res.json();
      setTestEmailResult(data);
    } catch (err) {
      setTestEmailResult({ success: false, detail: String(err) });
    } finally {
      setTestingEmail(false);
    }
  };

  if (!isOpen) return null;

  const handleToggle = (channelKey) => {
    setChannels((prev) => ({
      ...prev,
      [channelKey]: {
        ...prev[channelKey],
        enabled: !prev[channelKey].enabled,
      },
    }));
  };

  const handleSeverityChange = (channelKey, sev) => {
    setChannels((prev) => ({
      ...prev,
      [channelKey]: {
        ...prev[channelKey],
        minSeverity: sev,
      },
    }));
  };

  const handleSave = () => {
    localStorage.setItem('synapse_notification_prefs', JSON.stringify(channels));
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in">
      <div
        className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold dark:text-white text-slate-900">
                Notification Preferences & Webhook Hub
              </h3>
              <p className="text-[11px] text-slate-400">
                Configure alerting channels and severity filter triggers
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-800 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Channels List */}
        <div className="space-y-3">
          {/* Slack */}
          <div className="p-3.5 rounded-xl dark:bg-slate-950/60 bg-slate-50 border dark:border-slate-800 border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold dark:text-white text-slate-900">Slack Incident Room</span>
              </div>
              <input
                type="checkbox"
                checked={channels.slack.enabled}
                onChange={() => handleToggle('slack')}
                className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
              />
            </div>
            {channels.slack.enabled && (
              <div className="flex items-center justify-between gap-3 pt-1 text-xs">
                <input
                  type="text"
                  value={channels.slack.webhook}
                  onChange={(e) => setChannels({ ...channels, slack: { ...channels.slack, webhook: e.target.value } })}
                  className="flex-1 px-2.5 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-mono"
                />
                <select
                  value={channels.slack.minSeverity}
                  onChange={(e) => handleSeverityChange('slack', e.target.value)}
                  className="px-2 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-semibold"
                >
                  <option value="CRITICAL">Critical Only</option>
                  <option value="HIGH">High & Critical</option>
                  <option value="ALL">All Alerts</option>
                </select>
              </div>
            )}
          </div>

          {/* PagerDuty */}
          <div className="p-3.5 rounded-xl dark:bg-slate-950/60 bg-slate-50 border dark:border-slate-800 border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-rose-400" />
                <span className="text-xs font-bold dark:text-white text-slate-900">PagerDuty On-Call</span>
              </div>
              <input
                type="checkbox"
                checked={channels.pagerduty.enabled}
                onChange={() => handleToggle('pagerduty')}
                className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
              />
            </div>
            {channels.pagerduty.enabled && (
              <div className="flex items-center justify-between gap-3 pt-1 text-xs">
                <input
                  type="text"
                  value={channels.pagerduty.integrationKey}
                  onChange={(e) => setChannels({ ...channels, pagerduty: { ...channels.pagerduty, integrationKey: e.target.value } })}
                  className="flex-1 px-2.5 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-mono"
                />
                <select
                  value={channels.pagerduty.minSeverity}
                  onChange={(e) => handleSeverityChange('pagerduty', e.target.value)}
                  className="px-2 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-semibold"
                >
                  <option value="CRITICAL">Critical Only</option>
                  <option value="HIGH">High & Critical</option>
                </select>
              </div>
            )}
          </div>

          {/* Gmail SMTP Incident Alerting */}
          <div className="p-3.5 rounded-xl dark:bg-slate-950/60 bg-slate-50 border dark:border-slate-800 border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-sky-400" />
                <span className="text-xs font-bold dark:text-white text-slate-900">Gmail SMTP Admin Alert</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">
                  spareid9687@gmail.com
                </span>
              </div>
              <input
                type="checkbox"
                checked={channels.email?.enabled ?? true}
                onChange={() => handleToggle('email')}
                className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
              />
            </div>
            {channels.email?.enabled && (
              <div className="space-y-2 pt-1 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <input
                    type="email"
                    value={channels.email?.recipients || 'jayrajsinhbhatti9687@gmail.com'}
                    onChange={(e) => setChannels({ ...channels, email: { ...channels.email, recipients: e.target.value } })}
                    className="flex-1 px-2.5 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-mono"
                    placeholder="jayrajsinhbhatti9687@gmail.com"
                  />
                  <select
                    value={channels.email?.minSeverity || 'HIGH'}
                    onChange={(e) => handleSeverityChange('email', e.target.value)}
                    className="px-2 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-semibold"
                  >
                    <option value="CRITICAL">Critical Only</option>
                    <option value="HIGH">High & Critical</option>
                    <option value="ALL">All Alerts</option>
                  </select>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-slate-400">
                    Sends predicted failure reports to admin via Gmail SMTP
                  </span>
                  <button
                    type="button"
                    onClick={handleTestEmail}
                    disabled={testingEmail}
                    className="px-2.5 py-1 rounded text-[11px] font-semibold bg-sky-600/20 text-sky-400 hover:bg-sky-600/30 border border-sky-500/30 disabled:opacity-50 transition-colors"
                  >
                    {testingEmail ? 'Sending...' : 'Test Gmail Alert'}
                  </button>
                </div>
                {testEmailResult && (
                  <div className={`text-[11px] p-2 rounded ${testEmailResult.success ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'}`}>
                    {testEmailResult.success ? '✅ Test incident alert delivered to ' + (testEmailResult.recipient || 'admin') : `⚠️ ${testEmailResult.detail || testEmailResult.status}`}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* n8n Automation Webhook */}
          <div className="p-3.5 rounded-xl dark:bg-slate-950/60 bg-slate-50 border dark:border-slate-800 border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-bold dark:text-white text-slate-900">n8n Automated Workflow Trigger</span>
              </div>
              <input
                type="checkbox"
                checked={channels.n8n.enabled}
                onChange={() => handleToggle('n8n')}
                className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
              />
            </div>
            {channels.n8n.enabled && (
              <div className="pt-1 text-xs">
                <input
                  type="text"
                  value={channels.n8n.webhookUrl}
                  onChange={(e) => setChannels({ ...channels, n8n: { ...channels.n8n, webhookUrl: e.target.value } })}
                  className="w-full px-2.5 py-1 text-[11px] rounded dark:bg-slate-900 bg-white border dark:border-slate-700 border-slate-300 font-mono"
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 flex items-center justify-between">
          <span className="text-xs text-emerald-400 font-semibold">
            {savedSuccess && 'Preferences saved successfully!'}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg border dark:border-slate-700 border-slate-300 text-xs font-semibold hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg bg-synapse-600 hover:bg-synapse-500 text-white text-xs font-bold shadow-md shadow-synapse-600/25 flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              Save Preferences
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
