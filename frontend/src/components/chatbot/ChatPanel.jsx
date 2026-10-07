/**
 * frontend/src/components/chatbot/ChatPanel.jsx
 *
 * Dedicated Chat UI Panel embedded directly into DashboardPage.
 * Features:
 * - Full operational message feed with Markdown, code, and table rendering
 * - Dynamic quick-action prompt chips tailored to the active service/incident
 * - Context awareness: passes active service and incident ID with every message
 * - Live Server-Sent Events (SSE) streaming support
 * - Session history reset & active context controls
 */

import React, { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { sendChatMessage, streamChatMessage, clearSessionHistory } from '../../api/chatbot';
import {
  Sparkles,
  RotateCcw,
  Server,
  AlertTriangle,
  Zap,
  Radio,
  CheckCircle2,
} from 'lucide-react';

export default function ChatPanel({
  selectedServiceId,
  selectedIncident,
  onClearContext,
  className = '',
}) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('synapse_dashboard_chat_session') || null;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('synapse_dashboard_chat_session', sessionId);
    }
  }, [sessionId]);

  // Context metadata
  const activeService = selectedServiceId || null;
  const activeIncidentId = selectedIncident?.id || selectedIncident?.incident_id || null;

  // Context-aware dynamic chips
  const dynamicChips = [];
  if (activeService) {
    dynamicChips.push(`What's the risk score of ${activeService}?`);
    dynamicChips.push(`What does ${activeService} depend on?`);
    dynamicChips.push(`What breaks if ${activeService} fails?`);
    dynamicChips.push(`Diagnose ${activeService}`);
  }
  if (activeIncidentId) {
    dynamicChips.push(`Explain why incident ${activeIncidentId} happened`);
    dynamicChips.push(`Details on ${activeIncidentId}`);
  }
  if (dynamicChips.length === 0) {
    dynamicChips.push("What's the risk score of order-service?");
    dynamicChips.push('List open incidents');
    dynamicChips.push('What alerts are firing right now?');
    dynamicChips.push('What breaks if postgres-primary fails?');
    dynamicChips.push('Runbook for memory_leak');
  }

  const handleSendMessage = async (userText) => {
    if (!userText.trim() || isLoading) return;

    setError(null);
    const tempUserMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);
    setIsStreaming(true);
    setStreamText('');

    let accumulatedText = '';
    const tempBotId = `bot-${Date.now()}`;

    // Add placeholder streaming message
    setMessages((prev) => [
      ...prev,
      {
        id: tempBotId,
        role: 'assistant',
        content: '',
        isStreaming: true,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      await streamChatMessage(userText, {
        sessionId,
        service: activeService,
        incidentId: activeIncidentId,
        onChunk: (chunk) => {
          accumulatedText += chunk;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempBotId ? { ...m, content: accumulatedText } : m
            )
          );
        },
        onDone: (data) => {
          if (data.session_id) {
            setSessionId(data.session_id);
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempBotId
                ? {
                    ...m,
                    content: data.response || accumulatedText,
                    card: data.card,
                    isStreaming: false,
                  }
                : m
            )
          );
          setIsStreaming(false);
          setIsLoading(false);
        },
        onError: async (err) => {
          console.warn('Fallback to standard sendChatMessage:', err);
          const fallbackData = await sendChatMessage(userText, {
            sessionId,
            service: activeService,
            incidentId: activeIncidentId,
          });
          if (fallbackData.session_id) {
            setSessionId(fallbackData.session_id);
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === tempBotId
                ? {
                    ...m,
                    content: fallbackData.response,
                    card: fallbackData.card,
                    isStreaming: false,
                  }
                : m
            )
          );
          setIsStreaming(false);
          setIsLoading(false);
        },
      });
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempBotId
            ? {
                ...m,
                content:
                  '⚠️ Could not connect to GenAI Agent. Ensure `genai-agent` is running on port 8001.',
                isStreaming: false,
              }
            : m
        )
      );
      setIsStreaming(false);
      setIsLoading(false);
    }
  };

  const handleClearSession = async () => {
    if (sessionId) {
      try {
        await clearSessionHistory(sessionId);
      } catch (err) {
        console.warn('Failed to clear session on backend:', err);
      }
    }
    setMessages([]);
    setError(null);
    const newId = `dash-session-${Date.now()}`;
    setSessionId(newId);
    localStorage.setItem('synapse_dashboard_chat_session', newId);
  };

  return (
    <div
      className={`flex flex-col h-full rounded-2xl bg-slate-900/90 border border-slate-800 shadow-2xl backdrop-blur-xl overflow-hidden ${className}`}
    >
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950/60 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-600 to-purple-600 flex items-center justify-center shadow-md shadow-cyan-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-white tracking-wide">
                Ops Control Plane Chat
              </h3>
              <span className="flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Gemini ReAct
              </span>
            </div>
            <p className="text-[10px] text-slate-400">
              Autonomous reasoning & conversational SRE diagnostics
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleClearSession}
            title="Reset conversation session"
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors text-xs flex items-center gap-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="text-[10px]">Reset</span>
          </button>
        </div>
      </div>

      {/* Active Dashboard Context Strip */}
      {(activeService || activeIncidentId) && (
        <div className="flex items-center justify-between px-3.5 py-1.5 bg-cyan-950/30 border-b border-cyan-500/20 text-[11px]">
          <div className="flex items-center gap-2 overflow-x-auto">
            <span className="text-slate-400 font-medium text-[10px] uppercase tracking-wider">
              Context:
            </span>
            {activeService && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-mono text-[10px]">
                <Server className="w-3 h-3 text-cyan-400" />
                {activeService}
              </span>
            )}
            {activeIncidentId && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-red-500/10 text-red-300 border border-red-500/30 font-mono text-[10px]">
                <AlertTriangle className="w-3 h-3 text-red-400" />
                {activeIncidentId}
              </span>
            )}
          </div>
          {onClearContext && (
            <button
              onClick={onClearContext}
              className="text-[10px] text-slate-400 hover:text-slate-200 underline ml-2"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Quick Action Suggestion Chips */}
      <div className="px-3 py-2 bg-slate-950/30 border-b border-white/5 flex gap-1.5 overflow-x-auto scrollbar-none">
        {dynamicChips.slice(0, 4).map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(chip)}
            disabled={isLoading}
            className="shrink-0 text-[10px] px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 text-cyan-300 border border-white/10 hover:border-cyan-500/30 transition-all flex items-center gap-1"
          >
            <Zap className="w-2.5 h-2.5 text-cyan-400" />
            <span>{chip}</span>
          </button>
        ))}
      </div>

      {/* Message Feed */}
      <MessageList
        messages={messages}
        onSelectPrompt={handleSendMessage}
        isLoading={isLoading && !isStreaming}
      />

      {/* Message Input */}
      <div className="p-3 bg-slate-950/80 border-t border-white/10">
        <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}
