import type { AnyAgentId } from "./agent";

export type MessageRole = "user" | "assistant" | "system" | "tool";

export type MessageStatus = "pending" | "streaming" | "complete" | "error";

export type ExecutionStepStatus = "pending" | "running" | "completed" | "failed";

export interface ExecutionStep {
  id: string;
  title: string;
  status: ExecutionStepStatus;
  detail?: string;
}

export type DeliverableStatus = "generating" | "ready" | "failed";

export interface Deliverable {
  id: string;
  filename: string;
  fileType: string;
  sizeBytes: number;
  status: DeliverableStatus;
  createdAt: string;
}

export interface Citation {
  id: string;
  label: string;
  source: string;
  url?: string;
}

/** A block within a structured assistant response. */
export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "code"; language: string; code: string }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "warning"; text: string };

export interface ChatAttachment {
  id: string;
  filename: string;
  fileType: string;
  sizeBytes: number;
  status: "uploading" | "uploaded" | "error";
  errorMessage?: string;
  progress?: number;
  /** Relative path within the backend's uploads directory, once a real
   * upload has completed — lets agents/tools (CSV analysis, RAG ingestion)
   * read the actual file. Absent for local-only (not yet backed) uploads.
   */
  path?: string;
}

/** Auto mode's routing decision (see backend/app/agents/task_router.py) —
 * present only when the message was Auto-routed, so the UI can show
 * "AUTO MODE -> {label}" per the judge-facing explainability requirement.
 */
export interface TaskRouting {
  target: "agent" | "system_monitor" | "network_monitor" | "security_status" | "orchestrator";
  label: string;
  reason: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  status: MessageStatus;
  createdAt: string;
  agentId?: AnyAgentId;
  content?: ContentBlock[];
  /** Plain-text convenience for simple messages (user messages, errors). */
  text?: string;
  attachments?: ChatAttachment[];
  executionSteps?: ExecutionStep[];
  deliverables?: Deliverable[];
  citations?: Citation[];
  taskRouting?: TaskRouting;
  errorMessage?: string;
  toolName?: string;
}

/** Formats the conversation-export pipeline can produce (see
 * backend/app/services/conversation_export). Kept in sync with the
 * backend's `ExportFormat` literal.
 */
export type ExportFormat = "docx" | "pptx" | "xlsx" | "pdf";

export interface Conversation {
  id: string;
  title: string;
  agentId: AnyAgentId;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  agentId: AnyAgentId;
  updatedAt: string;
}
