import React, { useState, useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  List,
  ListItem,
  Divider,
  CircularProgress,
  Alert,
  Chip,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Mic as MicIcon,
  Stop as StopIcon,
  Clear as ClearIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '../../store';
import { sendMessage, fetchConversationHistory, createNewConversation } from '../../store/chatSlice';
import MessageBubble from './MessageBubble';
import ConversationList from './ConversationList';
import { Message } from '../../types/chat';
import { 
  useWebSocketConnection, 
  useTypingIndicator, 
  useConversationSubscription,
  useWebSocketStatus 
} from '../../hooks/useWebSocket';

const ChatInterface: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    currentConversation,
    messages,
    sendingMessage,
    loading,
    error,
    typingIndicator,
  } = useSelector((state: RootState) => state.chat);

  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // WebSocket hooks
  useWebSocketConnection();
  const { connectionStatus, connectionColor } = useWebSocketStatus();
  const { startTyping, stopTyping } = useTypingIndicator(currentConversation?.id || null);
  useConversationSubscription(currentConversation?.id || null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversation history when conversation changes
  useEffect(() => {
    if (currentConversation && messages.length === 0) {
      dispatch(fetchConversationHistory(currentConversation.id));
    }
  }, [currentConversation, dispatch, messages.length]);

  // Create a new conversation if none exists
  useEffect(() => {
    if (!currentConversation && !loading) {
      dispatch(createNewConversation({ title: 'New Chat' }));
    }
  }, [currentConversation, loading, dispatch]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || sendingMessage) return;

    const messageText = inputMessage;
    setInputMessage('');

    try {
      await dispatch(sendMessage({
        message: messageText,
        conversation_id: currentConversation?.id,
      })).unwrap();
    } catch (error) {
      // Error handled by slice
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      stopTyping();
      handleSendMessage();
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setInputMessage(value);
    
    // Trigger typing indicator
    if (value.trim() && !sendingMessage) {
      startTyping();
    } else {
      stopTyping();
    }
  };

  const handleVoiceInput = () => {
    if (isRecording) {
      // Stop recording
      setIsRecording(false);
      // TODO: Implement speech-to-text
    } else {
      // Start recording
      setIsRecording(true);
      // TODO: Implement speech-to-text
    }
  };

  const handleClearChat = () => {
    if (currentConversation) {
      dispatch(createNewConversation({ title: 'New Chat' }));
    }
  };

  const renderWelcomeMessage = () => (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        textAlign: 'center',
        p: 4,
      }}
    >
      <Typography variant="h4" gutterBottom color="primary">
        Welcome to Splunk MCP
      </Typography>
      <Typography variant="h6" color="text.secondary" gutterBottom>
        Ask questions about your data in natural language
      </Typography>
      <Box sx={{ mt: 3, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
        <Chip 
          label="Show me error logs from today" 
          variant="outlined" 
          onClick={() => setInputMessage("Show me error logs from today")}
          clickable
        />
        <Chip 
          label="Create a chart of CPU usage" 
          variant="outlined" 
          onClick={() => setInputMessage("Create a chart of CPU usage")}
          clickable
        />
        <Chip 
          label="Alert me when disk space is low" 
          variant="outlined" 
          onClick={() => setInputMessage("Alert me when disk space is low")}
          clickable
        />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Conversation Sidebar */}
      <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider' }}>
        <ConversationList />
      </Box>

      {/* Main Chat Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Chat Header */}
        <Paper
          elevation={1}
          sx={{
            p: 2,
            borderBottom: 1,
            borderColor: 'divider',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Box>
            <Typography variant="h6">
              {currentConversation?.title || 'New Conversation'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ask questions about your Splunk data
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title={`Connection: ${connectionStatus}`}>
              <IconButton size="small">
                {connectionStatus === 'connected' ? (
                  <WifiIcon color="success" />
                ) : (
                  <WifiOffIcon color="error" />
                )}
              </IconButton>
            </Tooltip>
            <Tooltip title="Clear conversation">
              <IconButton onClick={handleClearChat}>
                <ClearIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Paper>

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            {error}
          </Alert>
        )}

        {/* Messages Area */}
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
            backgroundColor: 'grey.50',
          }}
        >
          {messages.length === 0 && !loading ? (
            renderWelcomeMessage()
          ) : (
            <List sx={{ pb: 2 }}>
              {messages.map((message: Message, index: number) => (
                <React.Fragment key={message.id}>
                  <ListItem sx={{ px: 0, py: 1 }}>
                    <MessageBubble message={message} />
                  </ListItem>
                  {index < messages.length - 1 && <Divider />}
                </React.Fragment>
              ))}
              
              {/* Typing Indicator */}
              {typingIndicator && (
                <ListItem sx={{ px: 0, py: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={16} />
                    <Typography variant="body2" color="text.secondary">
                      Thinking...
                    </Typography>
                  </Box>
                </ListItem>
              )}
              
              <div ref={messagesEndRef} />
            </List>
          )}
        </Box>

        {/* Input Area */}
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderTop: 1,
            borderColor: 'divider',
          }}
        >
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <TextField
              ref={inputRef}
              fullWidth
              multiline
              maxRows={4}
              placeholder="Ask a question about your data..."
              value={inputMessage}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              disabled={sendingMessage}
              variant="outlined"
              size="small"
            />
            
            <Tooltip title="Attach file">
              <IconButton color="primary" disabled={sendingMessage}>
                <AttachFileIcon />
              </IconButton>
            </Tooltip>
            
            <Tooltip title={isRecording ? "Stop recording" : "Voice input"}>
              <IconButton
                color={isRecording ? "error" : "primary"}
                onClick={handleVoiceInput}
                disabled={sendingMessage}
              >
                {isRecording ? <StopIcon /> : <MicIcon />}
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Send message">
              <IconButton
                color="primary"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || sendingMessage}
              >
                {sendingMessage ? <CircularProgress size={24} /> : <SendIcon />}
              </IconButton>
            </Tooltip>
          </Box>
          
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Press Enter to send, Shift+Enter for new line
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
};

export default ChatInterface;