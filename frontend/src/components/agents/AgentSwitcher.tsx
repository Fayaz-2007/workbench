import { ChevronDown } from "lucide-react";
import { Dropdown } from "../common/Dropdown";
import { AGENTS, AUTO_AGENT, getAgentDisplay } from "../../services/mock/agents";
import type { AgentSelection } from "../../types";

export function AgentSwitcher({
  selectedAgentId,
  onSelect,
}: {
  selectedAgentId: AgentSelection;
  onSelect: (id: AgentSelection) => void;
}) {
  const selected = getAgentDisplay(selectedAgentId) ?? AUTO_AGENT;
  const Icon = selected.icon;
  const options = [AUTO_AGENT, ...AGENTS];

  return (
    <Dropdown
      trigger={
        <button className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-neutral-100">
          <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutral-100">
            <Icon className="size-4 text-neutral-600" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <span className="flex items-center gap-1 text-sm font-semibold text-neutral-900">
              {selected.name}
              <ChevronDown className="size-3.5 text-neutral-400" aria-hidden="true" />
            </span>
            <p className="truncate text-xs text-neutral-400">Local · Auto Model Selection</p>
          </div>
        </button>
      }
      items={options.map((agent) => ({
        id: agent.id,
        label: agent.name,
        icon: <agent.icon className="size-4 text-neutral-500" aria-hidden="true" />,
        onSelect: () => onSelect(agent.id as AgentSelection),
      }))}
    />
  );
}
