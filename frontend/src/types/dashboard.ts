export interface Panel {
  id: string;
  title: string;
  chart_type: string;
  position: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  data_source: string;
  query: string;
  chart_config: {
    x_axis?: string;
    y_axis?: string;
    color_scheme?: string;
    theme?: string;
    show_legend?: boolean;
    show_grid?: boolean;
    interactive?: boolean;
  };
  refresh_interval?: number;
  created_at: string;
  updated_at: string;
}

export interface Dashboard {
  id: string;
  title: string;
  description?: string;
  panels: Panel[];
  layout: {
    cols: number;
    rows: number;
    margin: [number, number];
    container_padding: [number, number];
  };
  theme: string;
  is_public: boolean;
  permissions: {
    view: string[];
    edit: string[];
    admin: string[];
  };
  tags: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDashboardRequest {
  title: string;
  description?: string;
  theme?: string;
  is_public?: boolean;
  tags?: string[];
}

export interface UpdateDashboardRequest {
  title?: string;
  description?: string;
  theme?: string;
  is_public?: boolean;
  tags?: string[];
  panels?: Panel[];
  layout?: Dashboard['layout'];
}

export interface CreatePanelRequest {
  title: string;
  chart_type: string;
  position: Panel['position'];
  data_source: string;
  query: string;
  chart_config?: Panel['chart_config'];
  refresh_interval?: number;
}

export interface DashboardState {
  dashboards: Dashboard[];
  currentDashboard: Dashboard | null;
  panels: Panel[];
  loading: boolean;
  saving: boolean;
  error: string | null;
  selectedPanel: Panel | null;
  isEditing: boolean;
}