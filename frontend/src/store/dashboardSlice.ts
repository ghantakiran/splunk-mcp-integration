import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
  DashboardState,
  Dashboard,
  Panel,
  CreateDashboardRequest,
  UpdateDashboardRequest,
  CreatePanelRequest
} from '../types/dashboard';
import { dashboardService } from '../services/dashboard';

const initialState: DashboardState = {
  dashboards: [],
  currentDashboard: null,
  panels: [],
  loading: false,
  saving: false,
  error: null,
  selectedPanel: null,
  isEditing: false,
};

// Async thunks
export const fetchDashboards = createAsyncThunk<Dashboard[], void>(
  'dashboard/fetchDashboards',
  async (_, { rejectWithValue }) => {
    try {
      return await dashboardService.getDashboards();
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch dashboards');
    }
  }
);

export const fetchDashboard = createAsyncThunk<Dashboard, string>(
  'dashboard/fetchDashboard',
  async (dashboardId, { rejectWithValue }) => {
    try {
      return await dashboardService.getDashboard(dashboardId);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch dashboard');
    }
  }
);

export const createDashboard = createAsyncThunk<Dashboard, CreateDashboardRequest>(
  'dashboard/createDashboard',
  async (dashboardData, { rejectWithValue }) => {
    try {
      return await dashboardService.createDashboard(dashboardData);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to create dashboard');
    }
  }
);

export const updateDashboard = createAsyncThunk<Dashboard, { id: string; data: UpdateDashboardRequest }>(
  'dashboard/updateDashboard',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      return await dashboardService.updateDashboard(id, data);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to update dashboard');
    }
  }
);

export const deleteDashboard = createAsyncThunk<string, string>(
  'dashboard/deleteDashboard',
  async (dashboardId, { rejectWithValue }) => {
    try {
      await dashboardService.deleteDashboard(dashboardId);
      return dashboardId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to delete dashboard');
    }
  }
);

export const createPanel = createAsyncThunk<Panel, { dashboardId: string; panelData: CreatePanelRequest }>(
  'dashboard/createPanel',
  async ({ dashboardId, panelData }, { rejectWithValue }) => {
    try {
      return await dashboardService.createPanel(dashboardId, panelData);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to create panel');
    }
  }
);

export const updatePanel = createAsyncThunk<Panel, { dashboardId: string; panelId: string; panelData: Partial<Panel> }>(
  'dashboard/updatePanel',
  async ({ dashboardId, panelId, panelData }, { rejectWithValue }) => {
    try {
      return await dashboardService.updatePanel(dashboardId, panelId, panelData);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to update panel');
    }
  }
);

export const deletePanel = createAsyncThunk<string, { dashboardId: string; panelId: string }>(
  'dashboard/deletePanel',
  async ({ dashboardId, panelId }, { rejectWithValue }) => {
    try {
      await dashboardService.deletePanel(dashboardId, panelId);
      return panelId;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to delete panel');
    }
  }
);

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    setCurrentDashboard: (state, action: PayloadAction<Dashboard | null>) => {
      state.currentDashboard = action.payload;
      state.panels = action.payload?.panels || [];
    },
    setSelectedPanel: (state, action: PayloadAction<Panel | null>) => {
      state.selectedPanel = action.payload;
    },
    setIsEditing: (state, action: PayloadAction<boolean>) => {
      state.isEditing = action.payload;
    },
    updatePanelPosition: (state, action: PayloadAction<{ panelId: string; position: Panel['position'] }>) => {
      const { panelId, position } = action.payload;
      const panel = state.panels.find(p => p.id === panelId);
      if (panel) {
        panel.position = position;
      }
      if (state.currentDashboard) {
        const dashboardPanel = state.currentDashboard.panels.find(p => p.id === panelId);
        if (dashboardPanel) {
          dashboardPanel.position = position;
        }
      }
    },
    clearError: (state) => {
      state.error = null;
    },
    addTempPanel: (state, action: PayloadAction<Panel>) => {
      state.panels.push(action.payload);
    },
    removeTempPanel: (state, action: PayloadAction<string>) => {
      state.panels = state.panels.filter(p => p.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch dashboards
      .addCase(fetchDashboards.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboards.fulfilled, (state, action) => {
        state.loading = false;
        state.dashboards = action.payload;
      })
      .addCase(fetchDashboards.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Fetch dashboard
      .addCase(fetchDashboard.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false;
        state.currentDashboard = action.payload;
        state.panels = action.payload.panels;
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Create dashboard
      .addCase(createDashboard.pending, (state) => {
        state.saving = true;
        state.error = null;
      })
      .addCase(createDashboard.fulfilled, (state, action) => {
        state.saving = false;
        state.dashboards.unshift(action.payload);
        state.currentDashboard = action.payload;
        state.panels = action.payload.panels;
      })
      .addCase(createDashboard.rejected, (state, action) => {
        state.saving = false;
        state.error = action.payload as string;
      })
      // Update dashboard
      .addCase(updateDashboard.pending, (state) => {
        state.saving = true;
        state.error = null;
      })
      .addCase(updateDashboard.fulfilled, (state, action) => {
        state.saving = false;
        const index = state.dashboards.findIndex(d => d.id === action.payload.id);
        if (index >= 0) {
          state.dashboards[index] = action.payload;
        }
        if (state.currentDashboard?.id === action.payload.id) {
          state.currentDashboard = action.payload;
          state.panels = action.payload.panels;
        }
      })
      .addCase(updateDashboard.rejected, (state, action) => {
        state.saving = false;
        state.error = action.payload as string;
      })
      // Delete dashboard
      .addCase(deleteDashboard.fulfilled, (state, action) => {
        state.dashboards = state.dashboards.filter(d => d.id !== action.payload);
        if (state.currentDashboard?.id === action.payload) {
          state.currentDashboard = null;
          state.panels = [];
        }
      })
      .addCase(deleteDashboard.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Create panel
      .addCase(createPanel.pending, (state) => {
        state.saving = true;
        state.error = null;
      })
      .addCase(createPanel.fulfilled, (state, action) => {
        state.saving = false;
        state.panels.push(action.payload);
        if (state.currentDashboard) {
          state.currentDashboard.panels.push(action.payload);
        }
      })
      .addCase(createPanel.rejected, (state, action) => {
        state.saving = false;
        state.error = action.payload as string;
      })
      // Update panel
      .addCase(updatePanel.fulfilled, (state, action) => {
        const index = state.panels.findIndex(p => p.id === action.payload.id);
        if (index >= 0) {
          state.panels[index] = action.payload;
        }
        if (state.currentDashboard) {
          const dashboardIndex = state.currentDashboard.panels.findIndex(p => p.id === action.payload.id);
          if (dashboardIndex >= 0) {
            state.currentDashboard.panels[dashboardIndex] = action.payload;
          }
        }
      })
      .addCase(updatePanel.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // Delete panel
      .addCase(deletePanel.fulfilled, (state, action) => {
        state.panels = state.panels.filter(p => p.id !== action.payload);
        if (state.currentDashboard) {
          state.currentDashboard.panels = state.currentDashboard.panels.filter(p => p.id !== action.payload);
        }
        if (state.selectedPanel?.id === action.payload) {
          state.selectedPanel = null;
        }
      })
      .addCase(deletePanel.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

export const {
  setCurrentDashboard,
  setSelectedPanel,
  setIsEditing,
  updatePanelPosition,
  clearError,
  addTempPanel,
  removeTempPanel,
} = dashboardSlice.actions;

export default dashboardSlice.reducer;