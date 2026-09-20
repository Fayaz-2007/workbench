export type ModelStatus = "active" | "idle" | "loading" | "error" | "disabled";

export interface ModelInfo {
  id: string;
  name: string;
  type: "general" | "code" | "vision" | "data" | "embedding";
  identifier: string;
  status: ModelStatus;
  contextLength: number;
  quantization: string;
  resourceRequirement: string;
  version: string;
}

export interface NewModelInput {
  name: string;
  type: ModelInfo["type"];
  identifier: string;
  capabilities: string;
  contextLength: number;
  quantization: string;
  status: ModelStatus;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  status: "success" | "failure" | "pending";
}

export interface AdminOverview {
  systemStatus: "development" | "operational" | "degraded" | "offline";
  externalConnections: "not_connected" | "connected" | "unknown";
  activeSessions: number | null;
  modelsOnline: number | null;
  modelsTotal: number | null;
  recentActivity: AuditLogEntry[];
}
