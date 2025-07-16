import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ChatState, Conversation, Message, ChatResponse, SendMessageRequest } from '../types/chat';
import { chatService } from '../services/chat';

const initialState: ChatState = {
  conversations: [],
  currentConversation: null,
  messages: [],
  loading: false,
  sendingMessage: false,
  error: null,
  isConnected: false,
  typingIndicator: false,
};

// Async thunks
export const fetchConversations = createAsyncThunk<Conversation[], void>(
  'chat/fetchConversations',
  async (_, { rejectWithValue }) => {
    try {
      return await chatService.getConversations();
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch conversations');
    }
  }
);

export const fetchConversationHistory = createAsyncThunk<Message[], string>(
  'chat/fetchConversationHistory',
  async (conversationId, { rejectWithValue }) => {
    try {
      const conversation = await chatService.getConversationHistory(conversationId);
      return conversation.messages || [];
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch conversation history');
    }
  }
);

export const sendMessage = createAsyncThunk<ChatResponse, SendMessageRequest>(
  'chat/sendMessage',
  async (messageData, { rejectWithValue }) => {
    try {
      return await chatService.sendMessage(messageData.message, messageData.conversation_id, messageData.context);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to send message');
    }
  }
);

export const createNewConversation = createAsyncThunk<Conversation, { title?: string }>(
  'chat/createNewConversation',
  async ({ title }, { rejectWithValue }) => {
    try {
      return await chatService.createConversation(title);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to create conversation');
    }
  }
);

export const deleteConversation = createAsyncThunk<string, string>(
  'chat/deleteConversation',
  async (conversationId, { rejectWithValue }) => {
    try {
      await chatService.deleteConversation(conversationId);
      return conversationId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to delete conversation');
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setCurrentConversation: (state, action: PayloadAction<Conversation | null>) => {
      state.currentConversation = action.payload;
      state.messages = [];
    },
    addMessage: (state, action: PayloadAction<Message>) => {
      state.messages.push(action.payload);
    },
    clearMessages: (state) => {
      state.messages = [];
    },
    setConnectionStatus: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },
    setTypingIndicator: (state, action: PayloadAction<boolean>) => {
      state.typingIndicator = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    updateConversationTitle: (state, action: PayloadAction<{ id: string; title: string }>) => {
      const { id, title } = action.payload;
      const conversation = state.conversations.find(c => c.id === id);
      if (conversation) {
        conversation.title = title;
      }
      if (state.currentConversation?.id === id) {
        state.currentConversation.title = title;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch conversations
      .addCase(fetchConversations.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.loading = false;
        state.conversations = action.payload;
      })
      .addCase(fetchConversations.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Fetch conversation history
      .addCase(fetchConversationHistory.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchConversationHistory.fulfilled, (state, action) => {
        state.loading = false;
        state.messages = action.payload;
      })
      .addCase(fetchConversationHistory.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Send message
      .addCase(sendMessage.pending, (state) => {
        state.sendingMessage = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.sendingMessage = false;
        state.messages.push(action.payload.message);
        
        // Update current conversation
        if (action.payload.conversation) {
          state.currentConversation = action.payload.conversation;
          
          // Update conversation in list
          const existingIndex = state.conversations.findIndex(
            c => c.id === action.payload.conversation.id
          );
          if (existingIndex >= 0) {
            state.conversations[existingIndex] = action.payload.conversation;
          } else {
            state.conversations.unshift(action.payload.conversation);
          }
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.sendingMessage = false;
        state.error = action.payload as string;
      })
      // Create new conversation
      .addCase(createNewConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload);
        state.currentConversation = action.payload;
        state.messages = [];
      })
      .addCase(createNewConversation.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Delete conversation
      .addCase(deleteConversation.fulfilled, (state, action) => {
        state.conversations = state.conversations.filter(c => c.id !== action.payload);
        if (state.currentConversation?.id === action.payload) {
          state.currentConversation = null;
          state.messages = [];
        }
      })
      .addCase(deleteConversation.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  setCurrentConversation,
  addMessage,
  clearMessages,
  setConnectionStatus,
  setTypingIndicator,
  clearError,
  updateConversationTitle,
} = chatSlice.actions;

export default chatSlice.reducer;