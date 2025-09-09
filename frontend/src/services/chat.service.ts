import { api, handleApiError } from './api';

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'ai';
  content: string;
  token_count?: number;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  bot_id?: string;
  title: string;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  bot_id?: string;
}

export interface MessageFeedback {
  rating: 1 | -1;
  comment?: string;
}

class ChatService {
  async createChatStream(request: ChatRequest): Promise<ReadableStream> {
    try {
      const response = await fetch(`${api.defaults.baseURL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      return response.body;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getSessions(): Promise<ChatSession[]> {
    try {
      const response = await api.get<ChatSession[]>('/sessions');
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    try {
      const response = await api.get<ChatMessage[]>(`/sessions/${sessionId}/messages`);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async searchMessages(query: string): Promise<ChatMessage[]> {
    try {
      const response = await api.get<ChatMessage[]>('/search', {
        params: { q: query },
      });
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async submitFeedback(messageId: string, feedback: MessageFeedback): Promise<void> {
    try {
      await api.post(`/messages/${messageId}/feedback`, feedback);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

export const chatService = new ChatService();