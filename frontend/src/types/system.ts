export interface DashboardMetric {
  label: string;
  value: string;
  hint: string;
  tone: "success" | "warning" | "danger" | "info";
}

export interface ModelListResponse {
  available_models: string[];
  current_model: string | null;
}

export interface ModelHealth {
  current_model: string | null;
  loaded: boolean;
  supported_models: string[];
}

export interface ModelRow {
  name: string;
  status: "Active" | "Idle";
  canUnload: boolean;
}

export interface TrendPoint {
  time: string;
  value: number;
}
