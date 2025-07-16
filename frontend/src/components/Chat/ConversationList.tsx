import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  IconButton,
  Typography,
  Button,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Divider,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Unarchive as UnarchiveIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { RootState, AppDispatch } from '../../store';
import {
  fetchConversations,
  setCurrentConversation,
  createNewConversation,
  deleteConversation,
  updateConversationTitle,
} from '../../store/chatSlice';
import { Conversation } from '../../types/chat';

const ConversationList: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { conversations, currentConversation, loading, error } = useSelector(
    (state: RootState) => state.chat
  );

  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    dispatch(fetchConversations());
  }, [dispatch]);

  const filteredConversations = conversations.filter(
    (conv) =>
      conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conv.last_message?.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateNew = () => {
    dispatch(createNewConversation({ title: 'New Conversation' }));
  };

  const handleSelectConversation = (conversation: Conversation) => {
    dispatch(setCurrentConversation(conversation));
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, conversation: Conversation) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setSelectedConversation(conversation);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedConversation(null);
  };

  const handleEditClick = () => {
    if (selectedConversation) {
      setNewTitle(selectedConversation.title);
      setEditDialogOpen(true);
    }
    handleMenuClose();
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    handleMenuClose();
  };

  const handleEditSave = () => {
    if (selectedConversation && newTitle.trim()) {
      dispatch(updateConversationTitle({
        id: selectedConversation.id,
        title: newTitle.trim(),
      }));
    }
    setEditDialogOpen(false);
    setNewTitle('');
  };

  const handleDeleteConfirm = () => {
    if (selectedConversation) {
      dispatch(deleteConversation(selectedConversation.id));
    }
    setDeleteDialogOpen(false);
  };

  const formatLastMessage = (conversation: Conversation) => {
    if (!conversation.last_message) return 'No messages yet';
    
    const content = conversation.last_message.content;
    return content.length > 50 ? `${content.substring(0, 50)}...` : content;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return format(date, 'HH:mm');
    } else if (diffInHours < 48) {
      return 'Yesterday';
    } else {
      return format(date, 'MMM dd');
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">Conversations</Typography>
          <IconButton onClick={handleCreateNew} color="primary">
            <AddIcon />
          </IconButton>
        </Box>

        {/* Search */}
        <TextField
          fullWidth
          size="small"
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
          }}
        />
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ m: 1 }}>
          {error}
        </Alert>
      )}

      {/* Conversations List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography color="text.secondary">Loading conversations...</Typography>
          </Box>
        ) : filteredConversations.length === 0 ? (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography color="text.secondary">
              {searchQuery ? 'No conversations found' : 'No conversations yet'}
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            {filteredConversations.map((conversation, index) => (
              <React.Fragment key={conversation.id}>
                <ListItem sx={{ p: 0 }}>
                  <ListItemButton
                    selected={currentConversation?.id === conversation.id}
                    onClick={() => handleSelectConversation(conversation)}
                    sx={{
                      py: 1.5,
                      px: 2,
                      '&.Mui-selected': {
                        backgroundColor: 'primary.50',
                        borderRight: 3,
                        borderColor: 'primary.main',
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Typography
                            variant="subtitle2"
                            sx={{
                              fontWeight: currentConversation?.id === conversation.id ? 600 : 400,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: '200px',
                            }}
                          >
                            {conversation.title}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={(e) => handleMenuOpen(e, conversation)}
                            sx={{ opacity: 0.7, '&:hover': { opacity: 1 } }}
                          >
                            <MoreVertIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 0.5 }}>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              fontSize: '0.75rem',
                            }}
                          >
                            {formatLastMessage(conversation)}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatDate(conversation.updated_at)}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              {conversation.message_count > 0 && (
                                <Chip
                                  label={conversation.message_count}
                                  size="small"
                                  sx={{ height: 16, fontSize: '0.65rem' }}
                                />
                              )}
                              {conversation.status === 'archived' && (
                                <Chip
                                  label="Archived"
                                  size="small"
                                  color="default"
                                  sx={{ height: 16, fontSize: '0.65rem' }}
                                />
                              )}
                            </Box>
                          </Box>
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
                {index < filteredConversations.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Box>

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={handleEditClick}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Rename
        </MenuItem>
        <MenuItem onClick={() => {}}>
          {selectedConversation?.status === 'archived' ? (
            <>
              <UnarchiveIcon fontSize="small" sx={{ mr: 1 }} />
              Unarchive
            </>
          ) : (
            <>
              <ArchiveIcon fontSize="small" sx={{ mr: 1 }} />
              Archive
            </>
          )}
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleDeleteClick} sx={{ color: 'error.main' }}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Rename Conversation</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Conversation Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleEditSave} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Conversation</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{selectedConversation?.title}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConversationList;