import { create } from 'zustand';
import { ChatSession, ChatMessage } from '@/types';
import { chatService } from '@/lib/api';

interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  
  fetchSessions: () => Promise<void>;
  createSession: (botId?: string) => Promise<ChatSession>;
  selectSession: (sessionId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  streamMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSession: null,
  messages: [],
  isLoading: false,
  isStreaming: false,
  error: null,
  
  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const sessions = await chatService.getSessions();
      set({ sessions, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to fetch sessions',
        isLoading: false,
      });
    }
  },
  
  createSession: async (botId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const session = await chatService.createSession(botId);
      set((state) => ({
        sessions: [session, ...state.sessions],
        currentSession: session,
        messages: [],
        isLoading: false,
      }));
      return session;
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to create session',
        isLoading: false,
      });
      throw error;
    }
  },
  
  selectSession: async (sessionId: string) => {
    const session = get().sessions.find((s) => s.id === sessionId);
    if (!session) return;
    
    set({ currentSession: session, isLoading: true, error: null });
    try {
      const messages = await chatService.getSessionMessages(sessionId);
      set({ messages, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to fetch messages',
        isLoading: false,
      });
    }
  },
  
  sendMessage: async (content: string) => {
    const currentSession = get().currentSession;
    if (!currentSession) return;
    
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSession.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    set((state) => ({
      messages: [...state.messages, userMessage],
    }));
    
    set({ isLoading: true, error: null });
    try {
      const response = await chatService.sendMessage(currentSession.id, content);
      set((state) => ({
        messages: [...state.messages, response],
        isLoading: false,
      }));
    } catch (error: any) {
      set({
        error: error.response?.data?.message || 'Failed to send message',
        isLoading: false,
      });
    }
  },
  
  streamMessage: async (content: string) => {
    const currentSession = get().currentSession;
    if (!currentSession) return;
    
    const userMessage: ChatMessage = {
      id: `temp-user-${Date.now()}`,
      session_id: currentSession.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    const assistantMessage: ChatMessage = {
      id: `temp-assistant-${Date.now()}`,
      session_id: currentSession.id,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    set((state) => ({
      messages: [...state.messages, userMessage, assistantMessage],
      isStreaming: true,
      error: null,
    }));
    
    await chatService.streamMessage(
      currentSession.id,
      content,
      (chunk) => {
        set((state) => {
          const messages = [...state.messages];
          const lastMessage = messages[messages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            lastMessage.content += chunk;
          }
          return { messages };
        });
      },
      () => {
        set({ isStreaming: false });
      },
      (error) => {
        set({
          error: error.message || 'Streaming failed',
          isStreaming: false,
        });
      }
    );
  },
  
  clearError: () => set({ error: null }),
}));