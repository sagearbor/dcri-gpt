import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, ThumbsUp, ThumbsDown } from 'lucide-react';
import { chatService, ChatMessage } from '../../services/chat.service';
import { useAuthStore } from '../../stores/auth.store';
import toast from 'react-hot-toast';

interface ChatInterfaceProps {
  sessionId?: string;
  botId?: string;
  onNewSession?: (sessionId: string) => void;
}

export default function ChatInterface({ sessionId, botId, onNewSession }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuthStore();

  useEffect(() => {
    if (sessionId) {
      loadMessages(sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadMessages = async (sessionId: string) => {
    try {
      const messages = await chatService.getSessionMessages(sessionId);
      setMessages(messages);
    } catch (error) {
      toast.error('Failed to load messages');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId || '',
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const stream = await chatService.createChatStream({
        message: userMessage,
        session_id: currentSessionId,
        bot_id: botId,
      });

      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let aiResponse = '';
      let newSessionId = currentSessionId;

      const tempAiMessage: ChatMessage = {
        id: `temp-ai-${Date.now()}`,
        session_id: currentSessionId || '',
        role: 'ai',
        content: '',
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, tempAiMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.session_id && !newSessionId) {
                newSessionId = data.session_id;
                setCurrentSessionId(newSessionId);
                onNewSession?.(newSessionId);
              }

              if (data.content) {
                aiResponse += data.content;
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage && lastMessage.role === 'ai') {
                    lastMessage.content = aiResponse;
                  }
                  return newMessages;
                });
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to send message');
      setMessages(prev => prev.filter(m => !m.id.startsWith('temp-')));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (messageId: string, rating: 1 | -1) => {
    try {
      await chatService.submitFeedback(messageId, { rating });
      toast.success('Feedback submitted');
    } catch (error) {
      toast.error('Failed to submit feedback');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Bot className="w-16 h-16 mb-4" />
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm">Ask me anything to get started</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`flex gap-3 max-w-[70%] ${
                  message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User className="w-5 h-5" />
                  ) : (
                    <Bot className="w-5 h-5" />
                  )}
                </div>

                <div className="flex flex-col gap-1">
                  <div
                    className={`px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>

                  {message.role === 'ai' && !message.id.startsWith('temp-') && (
                    <div className="flex gap-2 px-2">
                      <button
                        onClick={() => handleFeedback(message.id, 1)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Helpful"
                      >
                        <ThumbsUp className="w-4 h-4 text-gray-500" />
                      </button>
                      <button
                        onClick={() => handleFeedback(message.id, -1)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Not helpful"
                      >
                        <ThumbsDown className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Container */}
      <div className="border-t dark:border-gray-700 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}