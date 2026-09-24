/**
 * frontend/src/context/ChatbotContext.jsx
 *
 * React context providing global state for:
 * - messages list
 * - active sessionId
 * - pending remediation actions requiring human approval
 * - loading / streaming indicators
 */

import React, { createContext, useContext } from 'react';

export const ChatbotContext = createContext(null);

export function ChatbotProvider({ children }) {
  // TODO: Implement state management and actions provider
  return <ChatbotContext.Provider value={{}}>{children}</ChatbotContext.Provider>;
}

export function useChatbot() {
  return useContext(ChatbotContext);
}
