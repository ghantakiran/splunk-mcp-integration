import {
  Dashboard,
  Panel,
  CreateDashboardRequest,
  UpdateDashboardRequest,
  CreatePanelRequest
} from '../types/dashboard';
import apiClient from './api';

export class DashboardService {
  async getDashboards(): Promise<Dashboard[]> {
    return apiClient.get<Dashboard[]>('/dashboards');
  }

  async getDashboard(dashboardId: string): Promise<Dashboard> {
    return apiClient.get<Dashboard>(`/dashboards/${dashboardId}`);
  }

  async createDashboard(dashboardData: CreateDashboardRequest): Promise<Dashboard> {
    return apiClient.post<Dashboard>('/dashboards', dashboardData);
  }

  async updateDashboard(dashboardId: string, dashboardData: UpdateDashboardRequest): Promise<Dashboard> {
    return apiClient.put<Dashboard>(`/dashboards/${dashboardId}`, dashboardData);
  }

  async deleteDashboard(dashboardId: string): Promise<void> {
    return apiClient.delete(`/dashboards/${dashboardId}`);
  }

  async duplicateDashboard(dashboardId: string, newTitle?: string): Promise<Dashboard> {
    return apiClient.post<Dashboard>(`/dashboards/${dashboardId}/duplicate`, {
      title: newTitle,
    });
  }

  async shareDashboard(dashboardId: string, permissions: { view?: string[]; edit?: string[] }): Promise<Dashboard> {
    return apiClient.post<Dashboard>(`/dashboards/${dashboardId}/share`, permissions);
  }

  async createPanel(dashboardId: string, panelData: CreatePanelRequest): Promise<Panel> {
    return apiClient.post<Panel>(`/dashboards/${dashboardId}/panels`, panelData);
  }

  async updatePanel(dashboardId: string, panelId: string, panelData: Partial<Panel>): Promise<Panel> {
    return apiClient.put<Panel>(`/dashboards/${dashboardId}/panels/${panelId}`, panelData);
  }

  async deletePanel(dashboardId: string, panelId: string): Promise<void> {
    return apiClient.delete(`/dashboards/${dashboardId}/panels/${panelId}`);
  }

  async duplicatePanel(dashboardId: string, panelId: string): Promise<Panel> {
    return apiClient.post<Panel>(`/dashboards/${dashboardId}/panels/${panelId}/duplicate`);
  }

  async getPanelData(dashboardId: string, panelId: string): Promise<any> {
    return apiClient.get(`/dashboards/${dashboardId}/panels/${panelId}/data`);
  }

  async refreshPanelData(dashboardId: string, panelId: string): Promise<any> {
    return apiClient.post(`/dashboards/${dashboardId}/panels/${panelId}/refresh`);
  }

  async exportDashboard(dashboardId: string, format: 'json' | 'pdf' | 'png'): Promise<Blob> {
    const response = await apiClient.get(`/dashboards/${dashboardId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response as unknown as Blob;
  }

  async exportPanel(dashboardId: string, panelId: string, format: 'json' | 'png' | 'svg'): Promise<Blob> {
    const response = await apiClient.get(`/dashboards/${dashboardId}/panels/${panelId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response as unknown as Blob;
  }

  async searchDashboards(query: string): Promise<Dashboard[]> {
    return apiClient.get<Dashboard[]>('/dashboards/search', {
      params: { q: query },
    });
  }

  async getDashboardsByTag(tag: string): Promise<Dashboard[]> {
    return apiClient.get<Dashboard[]>('/dashboards', {
      params: { tag },
    });
  }

  async getPublicDashboards(): Promise<Dashboard[]> {
    return apiClient.get<Dashboard[]>('/dashboards/public');
  }
}

export const dashboardService = new DashboardService();