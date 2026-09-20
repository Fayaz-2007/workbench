import type { AgentDisplay } from "../../types";
import { cn } from "../../lib/utils";

export function AgentCard({
  agent,
  selected,
  onSelect,
}: {
  agent: AgentDisplay;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = agent.icon;
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "flex flex-col items-start gap-2.5 rounded-lg border p-3.5 text-left transition-colors",
        selected
          ? "border-neutral-900 bg-neutral-0 shadow-sm"
          : "border-neutral-150 bg-neutral-0 hover:border-neutral-300 hover:bg-neutral-25",
      )}
    >
      <div className="flex size-8 items-center justify-center rounded-md bg-neutral-100">
        <Icon className="size-4 text-neutral-700" aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-medium text-neutral-900">{agent.name}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-neutral-500">{agent.description}</p>
      </div>
    </button>
  );
}
