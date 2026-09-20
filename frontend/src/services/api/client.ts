import { Bot } from "lucide-react";
import { config } from "../../lib/config";
import { generateId } from "../../lib/utils";
import type {
  Agent,
  AgentId,
  AgentSelection,
  AnyAgentId,
  AuditLogEntry,
  ChatAttachment,
  ChatMessage,
  Conversation,
  ConversationSummary,
  DocumentSearchResult,
  KnowledgeDocument,
  ModelInfo,
  ModelStatus,
  NetworkStatus,
  NewModelInput,
  SecurityStatus,
  SystemStatus,
} from "../../types";
import type { AdminOverview } from "../../types/admin";
import { getAgentById } from "../mock/agents";
import { MOCK_AUDIT_LOGS } from "../mock/admin";
import { MOCK_CONVERSATIONS } from "../mock/conversations";
import { delay } from "../mock/delay";

/**
 * Centralized API surface for the workbench frontend.
 *
 * Agents, chat, and model registry calls go to the real FastAPI backend
 * (Segment 2 — see backend/app). Conversation history is still kept
 * client-side (the backend has no persistence layer yet — see
 * backend/app/database), and Network/System/Audit Logs remain on mock data
 * until a later segment adds real telemetry, matching what each page
 * currently claims ("waiting for backend telemetry", etc).
 */

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

interface ApiErrorBody {
  error?: { code?: string; message?: string };
}

/** Thin fetch wrapper: JSON in/out, and a clean, readable Error on failure —
 * never a raw fetch/parse exception or a leaked stack trace.
 */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new Error(`Could not reach the backend at ${config.apiBaseUrl}. Is it running?`);
  }

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      message = body.error?.message ?? message;
    } catch {
      // Response wasn't JSON (e.g. a proxy/500 HTML page) — keep the default.
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

interface BackendAgent {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
}

/** Agent identity/description comes from the backend; the icon is a purely
 * frontend concern, looked up locally by id (falling back to a generic icon
 * for any agent the backend adds that the frontend doesn't recognize yet).
 */
export async function getAgents(): Promise<Agent[]> {
  const backendAgents = await request<BackendAgent[]>("/api/agents");
  return backendAgents.map((agent) => ({
    id: agent.id as AgentId,
    name: agent.name,
    description: agent.description,
    icon: getAgentById(agent.id)?.icon ?? Bot,
  }));
}

// ---------------------------------------------------------------------------
// Conversations & messaging
// ---------------------------------------------------------------------------

// Conversation history has no backend store yet (see backend/app/database) —
// kept here, client-side, exactly as in Segment 1.
const conversationStore = new Map<string, Conversation>();

function seedConversation(summary: ConversationSummary): Conversation {
  return {
    ...summary,
    messages: [],
  };
}

for (const summary of MOCK_CONVERSATIONS) {
  conversationStore.set(summary.id, seedConversation(summary));
}

export async function getConversations(): Promise<ConversationSummary[]> {
  await delay(150);
  return Array.from(conversationStore.values())
    .map(({ id, title, agentId, updatedAt }) => ({ id, title, agentId, updatedAt }))
    .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
}

export async function getConversation(id: string): Promise<Conversation | null> {
  await delay(100);
  return conversationStore.get(id) ?? null;
}

export function createConversation(agentId: AgentId): Conversation {
  const conversation: Conversation = {
    id: generateId("conv"),
    title: "New conversation",
    agentId,
    updatedAt: new Date().toISOString(),
    messages: [],
  };
  conversationStore.set(conversation.id, conversation);
  return conversation;
}

export interface SendMessageParams {
  conversationId: string;
  agentId: AgentSelection;
  text: string;
  attachments?: ChatAttachment[];
}

interface BackendExecutionStep {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  detail: string | null;
}

interface BackendTaskRouting {
  target: "agent" | "system_monitor" | "network_monitor" | "security_status" | "orchestrator";
  agent_id: string;
  reason: string;
  confidence: number;
}

const TASK_ROUTING_LABELS: Record<string, string> = {
  system_monitor: "System Monitor",
  network_monitor: "Network Monitor",
  security_status: "Security Status",
  orchestrator: "Security Orchestrator",
};

interface BackendCitation {
  id: string;
  label: string;
  source: string;
}

interface BackendDeliverable {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: "ready" | "failed";
}

interface BackendChatResponse {
  conversation_id: string;
  agent: { id: string; name: string };
  task_routing: BackendTaskRouting | null;
  routing: { model_id: string; reason: string; score: number };
  response: string;
  execution: { status: string; steps: BackendExecutionStep[] };
  citations: BackendCitation[];
  deliverables: BackendDeliverable[];
}

/** Sends a user message through the real Agent Manager -> Model Router
 * pipeline and returns the assistant's reply.
 */
export async function sendMessage(params: SendMessageParams): Promise<ChatMessage> {
  const { conversationId, agentId, text, attachments } = params;
  const conversation = conversationStore.get(conversationId);

  const userMessage: ChatMessage = {
    id: generateId("msg"),
    role: "user",
    status: "complete",
    createdAt: new Date().toISOString(),
    text,
    attachments,
  };

  if (conversation) {
    conversation.messages.push(userMessage);
    if (conversation.title === "New conversation" && text.trim()) {
      conversation.title = text.trim().slice(0, 60);
    }
  }

  const backendResponse = await request<BackendChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      agent_id: agentId,
      message: text,
      conversation_id: conversationId,
      attachments: attachments?.map((a) => ({
        id: a.id,
        filename: a.filename,
        file_type: a.fileType,
        size_bytes: a.sizeBytes,
        path: a.path,
      })),
    }),
  });

  // In Auto mode, `agentId` is "auto" — the actually-resolved agent (or
  // monitor/orchestrator pseudo-target) only becomes known from the
  // response. Always use `backendResponse.agent.id` so the assistant
  // message (and its icon) reflect what actually handled the request.
  const resolvedAgentId = backendResponse.agent.id as AnyAgentId;

  const assistantMessage: ChatMessage = {
    id: generateId("msg"),
    role: "assistant",
    status: "complete",
    createdAt: new Date().toISOString(),
    agentId: resolvedAgentId,
    executionSteps: backendResponse.execution.steps.map((step) => ({
      id: step.id,
      title: step.title,
      status: step.status,
      detail: step.detail ?? undefined,
    })),
    content: [{ type: "text", text: backendResponse.response }],
    taskRouting: backendResponse.task_routing
      ? {
          target: backendResponse.task_routing.target,
          label: TASK_ROUTING_LABELS[backendResponse.task_routing.target] ?? backendResponse.agent.name,
          reason: backendResponse.task_routing.reason,
        }
      : undefined,
    citations: backendResponse.citations.map((c) => ({ id: c.id, label: c.label, source: c.source })),
    deliverables: backendResponse.deliverables.map((d) => ({
      id: d.id,
      filename: d.filename,
      fileType: d.file_type,
      sizeBytes: d.size_bytes,
      status: d.status,
      createdAt: new Date().toISOString(),
    })),
  };

  if (conversation) {
    conversation.messages.push(assistantMessage);
    conversation.updatedAt = new Date().toISOString();
    // Auto mode can resolve to a different agent each turn — keep the
    // conversation's sidebar icon reflecting whichever agent most
    // recently handled it (unchanged in manual mode, since it's always
    // the same agent anyway).
    conversation.agentId = resolvedAgentId;
  }

  return assistantMessage;
}

// ---------------------------------------------------------------------------
// File uploads
// ---------------------------------------------------------------------------

export interface UploadFileOptions {
  onProgress?: (progress: number) => void;
}

interface BackendUploadedFile {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  path: string;
}

/**
 * Uploads a file to the backend's local storage (POST /api/files/upload —
 * saved under the app's own `uploads/` directory, never anywhere else; see
 * backend/app/api/routes/files.py). `fetch` has no native upload-progress
 * event, so progress is reported as "started"/"done" rather than a smooth
 * percentage.
 */
export async function uploadFile(
  file: File,
  options: UploadFileOptions = {},
): Promise<ChatAttachment> {
  options.onProgress?.(10);

  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}/api/files/upload`, { method: "POST", body: formData });
  } catch {
    throw new Error(`Could not reach the backend at ${config.apiBaseUrl}. Is it running?`);
  }

  if (!response.ok) {
    let message = `Upload failed (HTTP ${response.status}).`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      message = body.error?.message ?? message;
    } catch {
      // Response wasn't JSON — keep the default message.
    }
    throw new Error(message);
  }

  options.onProgress?.(100);
  const uploaded = (await response.json()) as BackendUploadedFile;

  return {
    id: uploaded.id,
    filename: uploaded.filename,
    fileType: uploaded.file_type,
    sizeBytes: uploaded.size_bytes,
    status: "uploaded",
    path: uploaded.path,
  };
}

// ---------------------------------------------------------------------------
// Deliverables
// ---------------------------------------------------------------------------

/**
 * Downloads a generated deliverable's bytes from the backend's local
 * storage (GET /api/deliverables/{id} — files the Document Generation
 * Tool wrote under `generated/`; see backend/app/tools/document_generation.py).
 */
export async function downloadDeliverable(deliverableId: string): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}/api/deliverables/${encodeURIComponent(deliverableId)}`);
  } catch {
    throw new Error(`Could not reach the backend at ${config.apiBaseUrl}. Is it running?`);
  }

  if (!response.ok) {
    let message = `Download failed (HTTP ${response.status}).`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      message = body.error?.message ?? message;
    } catch {
      // Response wasn't JSON — keep the default message.
    }
    throw new Error(message);
  }

  return response.blob();
}

// ---------------------------------------------------------------------------
// Admin: overview
// ---------------------------------------------------------------------------

interface BackendActivityEntry {
  id: string;
  timestamp: string;
  action: string;
  resource: string;
  status: "success" | "failure" | "pending";
}

interface BackendAdminOverview {
  system_status: AdminOverview["systemStatus"];
  external_connections: AdminOverview["externalConnections"];
  active_sessions: number | null;
  models_online: number | null;
  models_total: number | null;
  recent_activity: BackendActivityEntry[];
}

export async function getAdminOverview(): Promise<AdminOverview> {
  const data = await request<BackendAdminOverview>("/api/admin/overview");
  return {
    systemStatus: data.system_status,
    externalConnections: data.external_connections,
    activeSessions: data.active_sessions,
    modelsOnline: data.models_online,
    modelsTotal: data.models_total,
    // The backend doesn't track user identity yet (real auth is a later
    // segment) — every entry is attributed to this single local session.
    recentActivity: data.recent_activity.map((entry): AuditLogEntry => ({
      id: entry.id,
      timestamp: entry.timestamp,
      user: "local",
      action: entry.action,
      resource: entry.resource,
      status: entry.status,
    })),
  };
}

// ---------------------------------------------------------------------------
// Admin: models
// ---------------------------------------------------------------------------

interface BackendModel {
  id: string;
  name: string;
  type: ModelInfo["type"];
  identifier: string;
  capabilities: string[];
  context_length: number;
  quantization: string;
  resource_class: "tiny" | "small" | "medium" | "large";
  status: ModelStatus;
  version: string;
}

const RESOURCE_CLASS_LABEL: Record<BackendModel["resource_class"], string> = {
  tiny: "Tiny · CPU-friendly",
  small: "Small · CPU-friendly",
  medium: "Medium · benefits from a GPU",
  large: "Large · GPU recommended",
};

function mapBackendModel(model: BackendModel): ModelInfo {
  return {
    id: model.id,
    name: model.name,
    type: model.type,
    identifier: model.identifier,
    status: model.status,
    contextLength: model.context_length,
    quantization: model.quantization,
    resourceRequirement: RESOURCE_CLASS_LABEL[model.resource_class] ?? model.resource_class,
    version: model.version,
  };
}

export async function getModels(): Promise<ModelInfo[]> {
  const models = await request<BackendModel[]>("/api/admin/models");
  return models.map(mapBackendModel);
}

export async function addModel(input: NewModelInput): Promise<ModelInfo> {
  const created = await request<BackendModel>("/api/models", {
    method: "POST",
    body: JSON.stringify({
      name: input.name,
      type: input.type,
      identifier: input.identifier,
      capabilities: input.capabilities,
      context_length: input.contextLength,
      quantization: input.quantization,
      status: input.status,
    }),
  });
  return mapBackendModel(created);
}

/** Registration is metadata-only on the backend too — this never deletes
 * real model weights, only the registry entry (see models/README.md).
 */
export async function deleteModel(modelId: string): Promise<void> {
  await request<unknown>(`/api/models/${encodeURIComponent(modelId)}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Monitoring: system / network / security (Phase F/G — real, local-only data)
// ---------------------------------------------------------------------------

interface BackendSystemStatus {
  hostname: string;
  operating_system: string;
  local_ip: string | null;
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  process_count: number;
  uptime_seconds: number;
}

export async function getSystemStatus(): Promise<SystemStatus> {
  const data = await request<BackendSystemStatus>("/api/system/status");
  return {
    hostname: data.hostname,
    operatingSystem: data.operating_system,
    localIp: data.local_ip,
    cpuPercent: data.cpu_percent,
    ramPercent: data.ram_percent,
    ramUsedGb: data.ram_used_gb,
    ramTotalGb: data.ram_total_gb,
    diskPercent: data.disk_percent,
    diskUsedGb: data.disk_used_gb,
    diskTotalGb: data.disk_total_gb,
    processCount: data.process_count,
    uptimeSeconds: data.uptime_seconds,
  };
}

interface BackendNetworkStatus {
  available: boolean;
  detail: string;
  local_count: number;
  external_count: number;
  connections: { local_address: string; remote_address: string | null; status: string; is_local: boolean; flags: string[] }[];
}

export async function getNetworkStatus(): Promise<NetworkStatus> {
  const data = await request<BackendNetworkStatus>("/api/network/status");
  return {
    available: data.available,
    detail: data.detail,
    localCount: data.local_count,
    externalCount: data.external_count,
    connections: data.connections.map((c) => ({
      localAddress: c.local_address,
      remoteAddress: c.remote_address,
      status: c.status,
      isLocal: c.is_local,
      flags: c.flags,
    })),
  };
}

export async function getSecurityStatus(): Promise<SecurityStatus> {
  return request<SecurityStatus>("/api/security/status");
}

// ---------------------------------------------------------------------------
// Admin: audit logs
// ---------------------------------------------------------------------------

/** No backend audit-log endpoint yet (real audit logging is a later
 * segment — see backend/README.md) — stays on mock data.
 */
export async function getAuditLogs(): Promise<AuditLogEntry[]> {
  await delay(300);
  return MOCK_AUDIT_LOGS;
}

// ---------------------------------------------------------------------------
// Knowledge base documents (Phase C)
// ---------------------------------------------------------------------------

interface BackendDocument {
  document_id: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
  ingested_at: string;
}

function mapBackendDocument(d: BackendDocument): KnowledgeDocument {
  return { documentId: d.document_id, filename: d.filename, docType: d.doc_type, chunkCount: d.chunk_count, ingestedAt: d.ingested_at };
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const docs = await request<BackendDocument[]>("/api/documents");
  return docs.map(mapBackendDocument);
}

/** Ingests an already-uploaded file (its `fileId`/path from `uploadFile()`)
 * into the local knowledge base — a separate, explicit step from upload so
 * a user can attach a file to one message without it silently becoming
 * permanent organizational knowledge.
 */
export async function ingestKnowledgeDocument(fileId: string): Promise<KnowledgeDocument> {
  const doc = await request<BackendDocument>("/api/documents/ingest", {
    method: "POST",
    body: JSON.stringify({ file_id: fileId }),
  });
  return mapBackendDocument(doc);
}

export async function deleteKnowledgeDocument(documentId: string): Promise<void> {
  await request<unknown>(`/api/documents/${encodeURIComponent(documentId)}`, { method: "DELETE" });
}

interface BackendSearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  text: string;
  score: number;
}

export async function searchKnowledgeBase(query: string, topK = 4): Promise<DocumentSearchResult[]> {
  const results = await request<BackendSearchResult[]>("/api/documents/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });
  return results.map((r) => ({
    chunkId: r.chunk_id,
    documentId: r.document_id,
    filename: r.filename,
    pageNumber: r.page_number,
    text: r.text,
    score: r.score,
  }));
}

// ---------------------------------------------------------------------------
// Tools (generic execution — used for report generation, etc.)
// ---------------------------------------------------------------------------

export interface ToolExecutionResult {
  success: boolean;
  output: unknown;
  error: string | null;
}

export async function executeTool(toolName: string, input: Record<string, unknown>): Promise<ToolExecutionResult> {
  return request<ToolExecutionResult>("/api/tools/execute", {
    method: "POST",
    body: JSON.stringify({ tool_name: toolName, input }),
  });
}
