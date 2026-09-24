/**
 * frontend/src/components/chatbot/ChatWindow.jsx
 *
 * Chat drawer body containing header, message list, auto-scroller, and input bar.
 */

import React, { useState, useEffect } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { sendChatMessage, clearSessionHistory } from '../../api/chatbot';

export default function ChatWindow({ onClose }) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('synapse_chat_session_id') || null;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('synapse_chat_session_id', sessionId);
    }
  }, [sessionId]);

  const handleSendMessage = async (userText) => {
    if (!userText.trim() || isLoading) return;

    setError(null);
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const data = await sendChatMessage(userText, sessionId);
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      const botMsg = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        card: data.card,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error('Chat message failed:', err);
      setError('Failed to reach Ops Co-Pilot agent. Ensure genai-agent is running on :8001.');
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: '⚠️ Service connection error: Could not connect to GenAI Agent backend.',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
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
    const newId = `session-${Date.now()}`;
    setSessionId(newId);
    localStorage.setItem('synapse_chat_session_id', newId);
  };

  return (
    <div className="flex flex-col h-[560px] w-[380px] sm:w-[440px] bg-slate-900/95 border border-white/15 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-sm">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="text-xs font-bold text-white tracking-wide">Synapse Ops Co-Pilot</h3>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <p className="text-[10px] text-gray-400">Autonomous SRE Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={handleClearSession}
            title="Reset conversation"
            className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors text-xs"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            onClick={onClose}
            title="Close chat"
            className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Message List */}
      <MessageList
        messages={messages}
        onSelectPrompt={handleSendMessage}
        isLoading={isLoading}
      />

      {/* Input */}
      <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
