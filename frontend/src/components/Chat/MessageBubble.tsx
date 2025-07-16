import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Avatar,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Code,
  Tooltip,
} from '@mui/material';
import {
  Person as PersonIcon,
  SmartToy as BotIcon,
  MoreVert as MoreVertIcon,
  ContentCopy as CopyIcon,
  Code as CodeIcon,
  ExpandMore as ExpandMoreIcon,
  Schedule as ScheduleIcon,
  DataObject as DataIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { Message } from '../../types/chat';
import { format } from 'date-fns';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const isUser = message.message_type === 'user';
  const isSystem = message.message_type === 'system';

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(message.content);
    handleMenuClose();
  };

  const handleCopySPL = () => {
    if (message.metadata?.spl_query) {
      navigator.clipboard.writeText(message.metadata.spl_query);
    }
    handleMenuClose();
  };

  const formatTimestamp = (timestamp: string) => {
    return format(new Date(timestamp), 'HH:mm');
  };

  const renderMetadata = () => {
    if (!message.metadata) return null;

    const { spl_query, execution_time, data_source, error_code } = message.metadata;

    return (
      <Box sx={{ mt: 2 }}>
        {/* SPL Query */}
        {spl_query && (
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CodeIcon fontSize="small" />
                <Typography variant="body2">SPL Query</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <SyntaxHighlighter
                language="splunk-spl"
                style={oneDark}
                customStyle={{
                  margin: 0,
                  borderRadius: 4,
                  fontSize: '0.875rem',
                }}
              >
                {spl_query}
              </SyntaxHighlighter>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Execution Stats */}
        <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
          {execution_time && (
            <Chip
              icon={<ScheduleIcon />}
              label={`${execution_time}ms`}
              size="small"
              variant="outlined"
            />
          )}
          {data_source && (
            <Chip
              icon={<DataIcon />}
              label={data_source}
              size="small"
              variant="outlined"
            />
          )}
          {error_code && (
            <Chip
              label={`Error: ${error_code}`}
              size="small"
              color="error"
              variant="outlined"
            />
          )}
        </Box>
      </Box>
    );
  };

  const renderMarkdownContent = (content: string) => {
    return (
      <ReactMarkdown
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: 4,
                  fontSize: '0.875rem',
                }}
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <Code
                sx={{
                  backgroundColor: 'grey.100',
                  px: 0.5,
                  py: 0.25,
                  borderRadius: 0.5,
                  fontSize: '0.875rem',
                }}
                {...props}
              >
                {children}
              </Code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  if (isSystem) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
        <Chip label={message.content} size="small" variant="outlined" />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        gap: 1,
        width: '100%',
      }}
    >
      {/* Avatar */}
      <Avatar
        sx={{
          bgcolor: isUser ? 'primary.main' : 'secondary.main',
          width: 36,
          height: 36,
        }}
      >
        {isUser ? <PersonIcon /> : <BotIcon />}
      </Avatar>

      {/* Message Content */}
      <Box
        sx={{
          maxWidth: '70%',
          minWidth: '200px',
        }}
      >
        <Paper
          elevation={1}
          sx={{
            p: 2,
            backgroundColor: isUser ? 'primary.main' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
            borderRadius: 2,
            borderTopLeftRadius: isUser ? 2 : 0.5,
            borderTopRightRadius: isUser ? 0.5 : 2,
          }}
        >
          {/* Message Header */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              mb: 1,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: isUser ? 'primary.contrastText' : 'text.secondary',
                opacity: 0.8,
              }}
            >
              {isUser ? 'You' : 'Assistant'} • {formatTimestamp(message.timestamp)}
            </Typography>
            
            <IconButton
              size="small"
              onClick={handleMenuOpen}
              sx={{
                color: isUser ? 'primary.contrastText' : 'text.secondary',
                opacity: 0.7,
                '&:hover': { opacity: 1 },
              }}
            >
              <MoreVertIcon fontSize="small" />
            </IconButton>
          </Box>

          {/* Message Text */}
          <Typography
            variant="body1"
            sx={{
              color: isUser ? 'primary.contrastText' : 'text.primary',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {isUser ? message.content : renderMarkdownContent(message.content)}
          </Typography>

          {/* Metadata (only for assistant messages) */}
          {!isUser && renderMetadata()}
        </Paper>
      </Box>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={handleCopyMessage}>
          <CopyIcon fontSize="small" sx={{ mr: 1 }} />
          Copy Message
        </MenuItem>
        {message.metadata?.spl_query && (
          <MenuItem onClick={handleCopySPL}>
            <CodeIcon fontSize="small" sx={{ mr: 1 }} />
            Copy SPL Query
          </MenuItem>
        )}
      </Menu>
    </Box>
  );
};

export default MessageBubble;