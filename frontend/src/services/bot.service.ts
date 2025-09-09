import { api, handleApiError } from './api';

export interface CustomBot {
  id: string;
  name: string;
  system_prompt: string;
  model_name: string;
  user_id: string;
  is_public: boolean;
  share_uuid?: string;
  created_at: string;
  updated_at: string;
}

export interface BotPermission {
  id: string;
  bot_id: string;
  user_id: string;
  permission_level: 'view' | 'chat';
}

export interface CreateBotRequest {
  name: string;
  system_prompt: string;
  model_name: string;
  is_public?: boolean;
}

export interface UpdateBotRequest {
  name?: string;
  system_prompt?: string;
  model_name?: string;
  is_public?: boolean;
}

export interface ShareBotRequest {
  user_email: string;
  permission_level: 'view' | 'chat';
}

class BotService {
  async getBots(): Promise<CustomBot[]> {
    try {
      const response = await api.get<CustomBot[]>('/bots');
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getBot(botId: string): Promise<CustomBot> {
    try {
      const response = await api.get<CustomBot>(`/bots/${botId}`);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async createBot(data: CreateBotRequest): Promise<CustomBot> {
    try {
      const response = await api.post<CustomBot>('/bots', data);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async updateBot(botId: string, data: UpdateBotRequest): Promise<CustomBot> {
    try {
      const response = await api.patch<CustomBot>(`/bots/${botId}`, data);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async deleteBot(botId: string): Promise<void> {
    try {
      await api.delete(`/bots/${botId}`);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async shareBot(botId: string, data: ShareBotRequest): Promise<void> {
    try {
      await api.post(`/bots/${botId}/share`, data);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async revokeShare(botId: string, userId: string): Promise<void> {
    try {
      await api.delete(`/bots/${botId}/share`, {
        data: { user_id: userId },
      });
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getBotPermissions(botId: string): Promise<BotPermission[]> {
    try {
      const response = await api.get<BotPermission[]>(`/bots/${botId}/permissions`);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

export const botService = new BotService();