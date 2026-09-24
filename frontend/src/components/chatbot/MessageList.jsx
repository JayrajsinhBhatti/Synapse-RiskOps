/**
 * frontend/src/components/chatbot/MessageList.jsx
 *
 * Renders user and bot message bubbles, text formatting, and nested cards (e.g. RiskScoreCard).
 */

import React, { useEffect, useRef } from 'react';
import RiskScoreCard from './cards/RiskScoreCard';

export default function MessageList({ messages = [], onSelectPrompt, isLoading = false }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm scrollbar-thin scrollbar-thumb-white/10">
      {messages.length === 0 && (
        <div className="text-center py-8 px-2 space-y-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center mx-auto shadow-lg shadow-cyan-500/20">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">Synapse RiskOps Co-Pilot</h4>
            <p className="text-xs text-gray-400 mt-1 max-w-xs mx-auto">
              Ask about any microservice’s health, risk score, failure predictions, or metrics.
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5 justify-center pt-2">
            {[
              'How is payment-service doing?',
              'Check health of api-gateway',
              'Risk score of order-service',
              'Status of auth-service',
            ].map((chip) => (
              <button
                key={chip}
                onClick={() => onSelectPrompt?.(chip)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/15 text-cyan-300 border border-white/10 transition-colors"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.map((msg, idx) => {
        const isUser = msg.role === 'user';
        return (
          <div
            key={msg.id || idx}
            className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1.5`}
          >
            <div className="flex items-center gap-1.5 text-[11px] text-gray-400 px-1">
              <span>{isUser ? 'You' : 'Ops Co-Pilot'}</span>
            </div>

            <div
              className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 shadow-md ${
                isUser
                  ? 'bg-cyan-600 text-white rounded-br-xs'
                  : 'bg-white/10 text-gray-100 border border-white/10 rounded-bl-xs'
              }`}
            >
              <div className="whitespace-pre-line leading-relaxed text-xs">
                {msg.content}
              </div>

              {/* Render Payload Cards */}
              {msg.card?.type === 'risk_score_card' && (
                <div className="mt-2 text-left">
                  <RiskScoreCard data={msg.card.data} />
                </div>
              )}
            </div>
          </div>
        );
      })}

      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-cyan-400 px-2 py-1">
          <div className="flex gap-1 items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" />
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.2s]" />
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.4s]" />
          </div>
          <span className="text-gray-400">Analyzing service telemetry...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
