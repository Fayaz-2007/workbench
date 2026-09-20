import { Menu, Server } from "lucide-react";
import { IconButton } from "../common/IconButton";
import { StatusDot } from "../common/StatusDot";
import { AgentSwitcher } from "../agents/AgentSwitcher";
import type { AgentDisplay, AgentSelection } from "../../types";

export function ChatHeader({
  agent,
  canSwitchAgent,
  onSelectAgent,
  onOpenMobileMenu,
}: {
  agent: AgentDisplay;
  canSwitchAgent: boolean;
  onSelectAgent: (id: AgentSelection) => void;
  onOpenMobileMenu: () => void;
}) {
  const Icon = agent.icon;
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-neutral-150 px-2 md:px-3">
      <div className="flex min-w-0 items-center gap-1">
        <IconButton label="Open menu" onClick={onOpenMobileMenu} className="md:hidden">
          <Menu className="size-4" />
        </IconButton>

        {canSwitchAgent ? (
          <AgentSwitcher selectedAgentId={agent.id as AgentSelection} onSelect={onSelectAgent} />
        ) : (
          <div className="flex items-center gap-2 px-2 py-1.5">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutral-100">
              <Icon className="size-4 text-neutral-600" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-neutral-900">{agent.name}</p>
              <p className="truncate text-xs text-neutral-400">Local · Auto Model Selection</p>
            </div>
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1.5 rounded-full border border-neutral-150 bg-neutral-0 px-2.5 py-1 text-xs font-medium text-neutral-600">
        <Server className="size-3.5 text-neutral-400" aria-hidden="true" />
        <span className="hidden sm:inline">Local Server</span>
        <StatusDot tone="success" />
      </div>
    </header>
  );
}
