import { Check, CircleDashed, Loader2, X } from "lucide-react";
import { cn } from "../../lib/utils";
import type { ExecutionStep } from "../../types";

const isActive = (steps: ExecutionStep[]) => steps.some((s) => s.status === "running");

export function ExecutionSteps({ steps }: { steps: ExecutionStep[] }) {
  if (steps.length === 0) return null;

  return (
    <div className="rounded-md border border-neutral-150 bg-neutral-25 px-3.5 py-3">
      <p className="mb-2 text-xs font-medium text-neutral-500">
        {isActive(steps) ? "Agent working" : "Agent steps"}
      </p>
      <ul className="space-y-1.5">
        {steps.map((step) => (
          <li key={step.id} className="flex gap-2 text-sm">
            <StepIcon status={step.status} />
            <span className="min-w-0">
              <span
                className={cn(
                  "block",
                  step.status === "completed" && "text-neutral-500",
                  step.status === "running" && "font-medium text-neutral-900",
                  step.status === "pending" && "text-neutral-400",
                  step.status === "failed" && "text-danger-500",
                )}
              >
                {step.title}
              </span>
              {step.detail && <span className="block text-xs text-neutral-400">{step.detail}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StepIcon({ status }: { status: ExecutionStep["status"] }) {
  if (status === "completed") {
    return (
      <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-success-500">
        <Check className="size-2.5 text-neutral-0" strokeWidth={3} aria-hidden="true" />
      </span>
    );
  }
  if (status === "running") {
    return <Loader2 className="size-4 shrink-0 animate-spin text-accent-500" aria-hidden="true" />;
  }
  if (status === "failed") {
    return (
      <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-danger-500">
        <X className="size-2.5 text-neutral-0" strokeWidth={3} aria-hidden="true" />
      </span>
    );
  }
  return <CircleDashed className="size-4 shrink-0 text-neutral-300" aria-hidden="true" />;
}
