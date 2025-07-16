import { Conversation, Message, ChatResponse, SendMessageRequest } from '../types/chat';
import apiClient from './api';

export class ChatService {
  async getConversations(): Promise<Conversation[]> {
    return apiClient.get<Conversation[]>('/chat/conversations');
  }

  async getConversationHistory(conversationId: string): Promise<{ messages: Message[] }> {
    return apiClient.get<{ messages: Message[] }>(`/chat/conversations/${conversationId}/messages`);
  }

  async sendMessage(
    message: string,
    conversationId?: string,
    context?: SendMessageRequest['context']
  ): Promise<ChatResponse> {
    const payload: SendMessageRequest = {
      message,
      conversation_id: conversationId,
      context,
    };

    return apiClient.post<ChatResponse>('/chat/message', payload);
  }

  async createConversation(title?: string): Promise<Conversation> {
    return apiClient.post<Conversation>('/chat/conversations', {
      title: title || 'New Conversation',
    });
  }

  async updateConversation(conversationId: string, data: { title?: string }): Promise<Conversation> {
    return apiClient.put<Conversation>(`/chat/conversations/${conversationId}`, data);
  }

  async deleteConversation(conversationId: string): Promise<void> {
    return apiClient.delete(`/chat/conversations/${conversationId}`);
  }

  async archiveConversation(conversationId: string): Promise<Conversation> {
    return apiClient.patch<Conversation>(`/chat/conversations/${conversationId}/archive`);
  }

  async unarchiveConversation(conversationId: string): Promise<Conversation> {
    return apiClient.patch<Conversation>(`/chat/conversations/${conversationId}/unarchive`);
  }

  async searchConversations(query: string): Promise<Conversation[]> {
    return apiClient.get<Conversation[]>('/chat/conversations/search', {
      params: { q: query },
    });
  }

  async searchMessages(query: string, conversationId?: string): Promise<Message[]> {
    const params: any = { q: query };
    if (conversationId) {
      params.conversation_id = conversationId;
    }

    return apiClient.get<Message[]>('/chat/messages/search', { params });
  }

  async regenerateResponse(messageId: string): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>(`/chat/messages/${messageId}/regenerate`);
  }

  async exportConversation(conversationId: string, format: 'json' | 'txt' | 'md'): Promise<Blob> {
    const response = await apiClient.get(`/chat/conversations/${conversationId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response as unknown as Blob;
  }
}

export const chatService = new ChatService();