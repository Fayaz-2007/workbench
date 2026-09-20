import type { LucideIcon } from "lucide-react";

/** Frontend agent abstraction. Users pick an agent, never a raw model. */
export type AgentId = "general" | "code" | "document" | "vision" | "data";

/** A concrete agent id, or "auto" — let the backend's Task Router pick the
 * agent for this request (see backend/app/agents/task_router.py). Kept
 * distinct from AgentId so real agent data (fetched from the backend)
 * never has to account for a pseudo-agent that doesn't really exist.
 */
export type AgentSelection = AgentId | "auto";

/** Auto mode's non-agent routing targets (see TaskRouting in
 * types/chat.ts) — deterministic local-data reads and the bounded
 * orchestrator, none of which are a real registered agent.
 */
export type SystemTargetId = "system_monitor" | "network_monitor" | "security_status" | "orchestrator";

/** Anything a chat message's `agentId`/an avatar lookup might resolve to:
 * a real agent, or one of the Auto-mode pseudo-targets above.
 */
export type AnyAgentId = AgentId | SystemTargetId;

export interface Agent {
  id: AgentId;
  name: string;
  description: string;
  icon: LucideIcon;
}

/** What agent-selection/avatar UI (cards, switcher, composer badge,
 * message avatar) needs to render — satisfied by a real `Agent`, the
 * "Auto" pseudo-agent, and the monitor/orchestrator pseudo-agents, so
 * those components don't need to special-case any of them.
 */
export interface AgentDisplay {
  id: AgentSelection | SystemTargetId;
  name: string;
  description: string;
  icon: LucideIcon;
}
