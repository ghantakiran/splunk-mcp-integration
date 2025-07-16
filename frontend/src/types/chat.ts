export interface Message {
  id: string;
  conversation_id: string;
  content: string;
  message_type: 'user' | 'assistant' | 'system';
  timestamp: string;
  metadata?: {
    spl_query?: string;
    execution_time?: number;
    data_source?: string;
    chart_config?: any;
    error_code?: string;
  };
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  status: 'active' | 'archived';
  last_message?: Message;
}

export interface ChatResponse {
  message: Message;
  conversation: Conversation;
  spl_query?: string;
  chart_data?: any;
  execution_stats?: {
    execution_time: number;
    rows_processed: number;
    data_source: string;
  };
}

export interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  loading: boolean;
  sendingMessage: boolean;
  error: string | null;
  isConnected: boolean;
  typingIndicator: boolean;
}

export interface SendMessageRequest {
  message: string;
  conversation_id?: string;
  context?: {
    previous_query?: string;
    chart_type?: string;
    time_range?: string;
  };
}