import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Share as ShareIcon,
  Download as DownloadIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { RootState, AppDispatch } from '../../store';
import {
  fetchDashboards,
  fetchDashboard,
  createDashboard,
  deleteDashboard,
  setCurrentDashboard,
} from '../../store/dashboardSlice';
import { Dashboard as DashboardType, CreateDashboardRequest } from '../../types/dashboard';

const Dashboard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const dispatch = useDispatch<AppDispatch>();
  const {
    dashboards,
    currentDashboard,
    loading,
    error,
  } = useSelector((state: RootState) => state.dashboard);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedDashboard, setSelectedDashboard] = useState<DashboardType | null>(null);
  const [newDashboard, setNewDashboard] = useState<CreateDashboardRequest>({
    title: '',
    description: '',
    theme: 'light',
    is_public: false,
    tags: [],
  });

  useEffect(() => {
    if (id) {
      dispatch(fetchDashboard(id));
    } else {
      dispatch(fetchDashboards());
      dispatch(setCurrentDashboard(null));
    }
  }, [id, dispatch]);

  const handleCreateDashboard = async () => {
    if (!newDashboard.title.trim()) return;
    
    try {
      await dispatch(createDashboard(newDashboard)).unwrap();
      setCreateDialogOpen(false);
      setNewDashboard({
        title: '',
        description: '',
        theme: 'light',
        is_public: false,
        tags: [],
      });
    } catch (error) {
      console.error('Failed to create dashboard:', error);
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, dashboard: DashboardType) => {
    setMenuAnchor(event.currentTarget);
    setSelectedDashboard(dashboard);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedDashboard(null);
  };

  const handleDeleteDashboard = async () => {
    if (selectedDashboard) {
      try {
        await dispatch(deleteDashboard(selectedDashboard.id)).unwrap();
        handleMenuClose();
      } catch (error) {
        console.error('Failed to delete dashboard:', error);
      }
    }
  };

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
  };

  if (id && currentDashboard) {
    // Render specific dashboard view
    return (
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {currentDashboard.title}
            </Typography>
            {currentDashboard.description && (
              <Typography variant="body1" color="text.secondary">
                {currentDashboard.description}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" startIcon={<EditIcon />}>
              Edit
            </Button>
            <Button variant="outlined" startIcon={<ShareIcon />}>
              Share
            </Button>
            <Button variant="outlined" startIcon={<DownloadIcon />}>
              Export
            </Button>
          </Box>
        </Box>

        {/* Dashboard Panels */}
        {currentDashboard.panels.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              No panels yet
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Start by adding your first panel to this dashboard
            </Typography>
            <Button variant="contained" startIcon={<AddIcon />} sx={{ mt: 2 }}>
              Add Panel
            </Button>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {currentDashboard.panels.map((panel) => (
              <Grid item xs={12} md={6} lg={4} key={panel.id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {panel.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {panel.chart_type} chart
                    </Typography>
                    <Box sx={{ mt: 2, height: 200, bgcolor: 'grey.100', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        Chart placeholder
                      </Typography>
                    </Box>
                  </CardContent>
                  <CardActions>
                    <Button size="small" startIcon={<ViewIcon />}>
                      View
                    </Button>
                    <Button size="small" startIcon={<EditIcon />}>
                      Edit
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    );
  }

  // Render dashboard list view
  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Dashboards</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Dashboard
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : dashboards.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No dashboards yet
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Create your first dashboard to start visualizing your data
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{ mt: 2 }}
          >
            Create Dashboard
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {dashboards.map((dashboard) => (
            <Grid item xs={12} md={6} lg={4} key={dashboard.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <Typography variant="h6" gutterBottom>
                      {dashboard.title}
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, dashboard)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </Box>
                  
                  {dashboard.description && (
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {dashboard.description}
                    </Typography>
                  )}
                  
                  <Box sx={{ display: 'flex', gap: 0.5, mb: 2, flexWrap: 'wrap' }}>
                    <Chip label={`${dashboard.panels.length} panels`} size="small" />
                    <Chip label={dashboard.theme} size="small" variant="outlined" />
                    {dashboard.is_public && (
                      <Chip label="Public" size="small" color="success" />
                    )}
                  </Box>
                  
                  {dashboard.tags.length > 0 && (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {dashboard.tags.map((tag) => (
                        <Chip key={tag} label={tag} size="small" variant="outlined" />
                      ))}
                    </Box>
                  )}
                </CardContent>
                
                <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Updated {formatDate(dashboard.updated_at)}
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => window.open(`/dashboards/${dashboard.id}`, '_blank')}
                  >
                    Open
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Dashboard Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Dashboard</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Dashboard Title"
            value={newDashboard.title}
            onChange={(e) => setNewDashboard({ ...newDashboard, title: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Description (optional)"
            value={newDashboard.description}
            onChange={(e) => setNewDashboard({ ...newDashboard, description: e.target.value })}
            margin="normal"
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateDashboard} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dashboard Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <ShareIcon fontSize="small" sx={{ mr: 1 }} />
          Share
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <DownloadIcon fontSize="small" sx={{ mr: 1 }} />
          Export
        </MenuItem>
        <MenuItem onClick={handleDeleteDashboard} sx={{ color: 'error.main' }}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default Dashboard;