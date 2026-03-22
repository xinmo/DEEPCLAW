export interface ChannelRuntimeStatus {
  installed: boolean;
  available: boolean;
  running: boolean;
  state: string;
  message: string;
  updated_at?: string | null;
}

export interface ChannelSummary {
  name: string;
  label: string;
  enabled: boolean;
  configured: boolean;
  status: string;
  status_message: string;
  updated_at?: string | null;
}

export interface ChannelListResponse {
  channels: ChannelSummary[];
}

export interface QQChannelConfigPayload {
  enabled: boolean;
  app_id: string;
  secret: string;
  allow_from: string[];
}

export interface QQChannelDetail {
  name: string;
  label: string;
  enabled: boolean;
  configured: boolean;
  config: QQChannelConfigPayload;
  validation_errors: string[];
  runtime: ChannelRuntimeStatus;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ChannelConnectivityCheck {
  key: string;
  label: string;
  status: "success" | "warning" | "error" | "info";
  message: string;
}

export interface QQChannelTestResult {
  success: boolean;
  state: "success" | "warning" | "error";
  message: string;
  tested_at: string;
  checks: ChannelConnectivityCheck[];
  runtime: ChannelRuntimeStatus;
}

export interface ChannelLogEntry {
  timestamp: string;
  level: string;
  source: string;
  message: string;
}

export interface QQChannelLogsResponse {
  channel: string;
  entries: ChannelLogEntry[];
}
