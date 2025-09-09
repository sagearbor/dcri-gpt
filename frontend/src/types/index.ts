export interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  bot_id?: string;
  title: string;
  created_at: string;
  updated_at: string;
  last_message_at?: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  updated_at: string;
  token_count?: number;
  feedback?: MessageFeedback;
}

export interface MessageFeedback {
  id: string;
  message_id: string;
  user_id: string;
  rating: number;
  comment?: string;
  created_at: string;
}

export interface CustomBot {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens: number;
  owner_id: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  tools?: BotTool[];
  permissions?: BotPermission[];
}

export interface BotTool {
  id: string;
  bot_id: string;
  tool_type: 'sql' | 'sharepoint' | 'box' | 'custom';
  configuration: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface BotPermission {
  id: string;
  bot_id: string;
  user_id: string;
  permission: 'view' | 'use' | 'edit' | 'admin';
  created_at: string;
}

export interface TokenUsageLog {
  id: string;
  user_id: string;
  session_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_sessions: number;
  total_messages: number;
  total_tokens: number;
  total_cost: number;
  daily_stats: DailyStat[];
}

export interface DailyStat {
  date: string;
  sessions: number;
  messages: number;
  tokens: number;
  cost: number;
  active_users: number;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
}