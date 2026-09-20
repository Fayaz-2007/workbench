import { Activity, Bot, Code2, FileText, Image, Network, ShieldCheck, Sparkles, Table2, Workflow } from "lucide-react";
import type { Agent, AgentDisplay, AgentSelection, AnyAgentId, SystemTargetId } from "../../types";

export const AGENTS: Agent[] = [
  {
    id: "general",
    name: "General Agent",
    description: "Everyday questions, drafting, and general assistance.",
    icon: Bot,
  },
  {
    id: "code",
    name: "Code Agent",
    description: "Read, write, and reason about source code.",
    icon: Code2,
  },
  {
    id: "document",
    name: "Document Agent",
    description: "Summarize, draft, and edit documents and reports.",
    icon: FileText,
  },
  {
    id: "vision",
    name: "Vision Agent",
    description: "Analyze images, scans, and diagrams.",
    icon: Image,
  },
  {
    id: "data",
    name: "Data Agent",
    description: "Explore spreadsheets and tabular data.",
    icon: Table2,
  },
];

/** Local-only pseudo-agent: selecting it sends no concrete `agent_id`, so
 * the backend's Task Router (app/agents/task_router.py) picks a real agent
 * per request. Never returned by the backend's `/api/agents` — this is a
 * UI affordance only.
 */
export const AUTO_AGENT: AgentDisplay = {
  id: "auto",
  name: "Auto",
  description: "Automatically selects the best agent for your request.",
  icon: Sparkles,
};

/** Auto mode's non-agent routing targets (Phase E/F/G/H) — deterministic
 * local reads and the bounded orchestrator, each with its own avatar so
 * chat messages from these paths render distinctly from a real agent.
 */
export const SYSTEM_TARGET_AGENTS: Record<SystemTargetId, AgentDisplay> = {
  system_monitor: { id: "system_monitor", name: "System Monitor", description: "Local CPU/RAM/disk status.", icon: Activity },
  network_monitor: { id: "network_monitor", name: "Network Monitor", description: "Local vs. external connections.", icon: Network },
  security_status: { id: "security_status", name: "Security Status", description: "Data sovereignty status.", icon: ShieldCheck },
  orchestrator: { id: "orchestrator", name: "Security Orchestrator", description: "Multi-step local security assessment.", icon: Workflow },
};

export function getAgentById(id: string): Agent | undefined {
  return AGENTS.find((agent) => agent.id === id);
}

/** Resolves any selection — a real agent id or "auto" — to something
 * with an icon/name/description to render. Use this (not `getAgentById`)
 * wherever the UI might be showing the Auto option.
 */
export function getAgentDisplay(selection: AgentSelection): AgentDisplay | undefined {
  if (selection === "auto") return AUTO_AGENT;
  return getAgentById(selection);
}

/** Resolves anything a chat message's `agentId` might be — a real agent,
 * or one of the Auto-mode pseudo-targets — for message avatar rendering.
 */
export function getAnyAgentDisplay(id: AnyAgentId | undefined): AgentDisplay | undefined {
  if (!id) return undefined;
  if (id in SYSTEM_TARGET_AGENTS) return SYSTEM_TARGET_AGENTS[id as SystemTargetId];
  return getAgentById(id);
}

/** Collapses a conversation's last `agentId` down to something the agent
 * switcher can hold as its selection. A pseudo-target (system_monitor,
 * etc.) only ever comes from Auto mode's routing, so it maps back to
 * "auto" rather than a switchable option of its own.
 */
export function toAgentSelection(id: AnyAgentId): AgentSelection {
  if (id === "system_monitor" || id === "network_monitor" || id === "security_status" || id === "orchestrator") {
    return "auto";
  }
  return id;
}
