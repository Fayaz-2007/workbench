import { Sparkles } from "lucide-react";
import { formatTimestamp } from "../../lib/utils";
import { getAnyAgentDisplay } from "../../services/mock/agents";
import type { ChatMessage } from "../../types";
import { ContentBlockRenderer } from "./ContentBlockRenderer";
import { ExecutionSteps } from "../execution/ExecutionSteps";
import { DeliverableCard } from "../deliverables/DeliverableCard";
import { CitationList } from "./CitationList";
import { GenerateReportButton } from "./GenerateReportButton";

export function AssistantMessage({ message }: { message: ChatMessage }) {
  const agent = getAnyAgentDisplay(message.agentId ?? "general");
  const Icon = agent?.icon;

  return (
    <div className="flex gap-3">
      <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutral-900">
        {Icon && <Icon className="size-3.5 text-neutral-0" aria-hidden="true" />}
      </div>
      <div className="min-w-0 flex-1 space-y-3">
        {message.taskRouting && (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-accent-50 px-2.5 py-1 text-xs font-medium text-accent-700">
            <Sparkles className="size-3.5" aria-hidden="true" />
            AUTO MODE
            <span className="text-accent-400">&rarr;</span>
            {message.taskRouting.label}
          </div>
        )}

        {message.executionSteps && message.executionSteps.length > 0 && (
          <ExecutionSteps steps={message.executionSteps} />
        )}

        {message.content?.map((block, i) => <ContentBlockRenderer key={i} block={block} />)}

        {message.deliverables && message.deliverables.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {message.deliverables.map((deliverable) => (
              <DeliverableCard key={deliverable.id} deliverable={deliverable} />
            ))}
          </div>
        )}

        {message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}

        {message.taskRouting?.target === "orchestrator" && <GenerateReportButton message={message} />}

        <p className="text-xs text-neutral-400">{formatTimestamp(message.createdAt)}</p>
      </div>
    </div>
  );
}
