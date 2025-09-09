import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react';
import { useChatStore } from '@/stores/chatStore';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/types';

const MessageBubble: React.FC<{ message: ChatMessage; isOwn: boolean }> = ({ message, isOwn }) => {
  const [copied, setCopied] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<'up' | 'down' | null>(null);

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedbackGiven(type);
    // TODO: Send feedback to API
  };

  const formatMessage = (content: string) => {
    // Check for code blocks
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex, match.index),
        });
      }

      // Add code block
      parts.push({
        type: 'code',
        language: match[1] || 'plaintext',
        content: match[2].trim(),
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex),
      });
    }

    return parts.length > 0 ? parts : [{ type: 'text', content }];
  };

  return (
    <div className={cn('flex items-start gap-3 mb-4', isOwn ? 'flex-row-reverse' : '')}>
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isOwn ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
      )}>
        {isOwn ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={cn('flex-1 max-w-[70%]', isOwn ? 'items-end' : 'items-start')}>
        <div className={cn(
          'rounded-lg px-4 py-3 shadow-sm',
          isOwn 
            ? 'bg-primary text-primary-foreground' 
            : 'bg-card border border-border'
        )}>
          <div className="space-y-2">
            {formatMessage(message.content).map((part, index) => {
              if (part.type === 'code') {
                return (
                  <div key={index} className="relative group">
                    <div className="bg-gray-900 dark:bg-gray-950 rounded-md p-3 mt-2">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-gray-400">{part.language}</span>
                        <button
                          onClick={() => handleCopy(part.content)}
                          className="text-gray-400 hover:text-white transition-colors"
                        >
                          {copied ? (
                            <Check className="w-4 h-4" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                      <pre className="text-sm text-gray-100 overflow-x-auto">
                        <code>{part.content}</code>
                      </pre>
                    </div>
                  </div>
                );
              }
              return (
                <p key={index} className="whitespace-pre-wrap break-words">
                  {part.content}
                </p>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-muted-foreground">
            {new Date(message.created_at).toLocaleTimeString()}
          </span>
          
          {!isOwn && (
            <div className="flex gap-1">
              <button
                onClick={() => handleFeedback('up')}
                className={cn(
                  'p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',
                  feedbackGiven === 'up' && 'text-green-600'
                )}
              >
                <ThumbsUp className="w-3 h-3" />
              </button>
              <button
                onClick={() => handleFeedback('down')}
                className={cn(
                  'p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',
                  feedbackGiven === 'down' && 'text-red-600'
                )}
              >
                <ThumbsDown className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const TypingIndicator: React.FC = () => (
  <div className="flex items-start gap-3 mb-4">
    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center">
      <Bot className="w-4 h-4" />
    </div>
    <div className="bg-card border border-border rounded-lg px-4 py-3">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  </div>
);

export const ChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { messages, isStreaming, streamMessage, currentSession } = useChatStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const message = input.trim();
    setInput('');
    await streamMessage(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-12 h-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Type your message below to begin chatting with the AI assistant
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isOwn={message.role === 'user'}
              />
            ))}
            {isStreaming && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={currentSession ? "Type your message..." : "Create a session to start chatting"}
              disabled={!currentSession || isStreaming}
              className="w-full px-4 py-3 rounded-lg border border-input bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              rows={1}
              style={{
                minHeight: '48px',
                maxHeight: '120px',
              }}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming || !currentSession}
            size="icon"
            className="h-12 w-12"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </div>
        
        {isStreaming && (
          <p className="text-xs text-muted-foreground mt-2">
            AI is typing...
          </p>
        )}
      </div>
    </div>
  );
};