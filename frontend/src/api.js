/**
 * API client for Deep Research Agent backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Health check
 */
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

/**
 * Run LLM Council deliberation
 */
export const runCouncil = async (question) => {
  const response = await api.post('/council', {
    question,
    mode: 'council'
  });
  return response.data;
};

/**
 * Run DxO research workflow
 */
export const runDxO = async (question) => {
  const response = await api.post('/dxo', {
    question,
    mode: 'dxo'
  });
  return response.data;
};

/**
 * Create a new conversation
 */
export const createConversation = async (initialMessage = null) => {
  const response = await api.post('/api/conversations', {
    initial_message: initialMessage
  });
  return response.data;
};

/**
 * List all conversations
 */
export const listConversations = async () => {
  const response = await api.get('/api/conversations');
  return response.data;
};

/**
 * Get a specific conversation
 */
export const getConversation = async (conversationId) => {
  const response = await api.get(`/api/conversations/${conversationId}`);
  return response.data;
};

/**
 * Add message to conversation
 */
export const addMessage = async (conversationId, question, mode) => {
  const response = await api.post(`/api/conversations/${conversationId}/message`, {
    question,
    mode
  });
  return response.data;
};

/**
 * Delete a conversation
 */
export const deleteConversation = async (conversationId) => {
  const response = await api.delete(`/api/conversations/${conversationId}`);
  return response.data;
};

export default api;
