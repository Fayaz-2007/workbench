import { ShieldHalf } from "lucide-react";
import { AGENTS, AUTO_AGENT } from "../../services/mock/agents";
import { AgentCard } from "../agents/AgentCard";
import type { AgentSelection } from "../../types";

export function WelcomeState({
  selectedAgentId,
  onSelectAgent,
}: {
  selectedAgentId: AgentSelection;
  onSelectAgent: (id: AgentSelection) => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center px-4 py-10">
      <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-neutral-900">
        <ShieldHalf className="size-6 text-neutral-0" aria-hidden="true" />
      </div>
      <h1 className="text-xl font-semibold text-neutral-900">Sovereign AI Workbench</h1>
      <p className="mt-1.5 text-sm text-neutral-500">Your private AI workspace for confidential work.</p>

      <div className="mt-8 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2">
        <AgentCard
          agent={AUTO_AGENT}
          selected={selectedAgentId === "auto"}
          onSelect={() => onSelectAgent("auto")}
        />
        {AGENTS.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            selected={agent.id === selectedAgentId}
            onSelect={() => onSelectAgent(agent.id)}
          />
        ))}
      </div>
    </div>
  );
}
