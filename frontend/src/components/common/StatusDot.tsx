import { cn } from "../../lib/utils";

export type StatusTone = "success" | "warning" | "danger" | "neutral" | "info";

const TONE_CLASSES: Record<StatusTone, string> = {
  success: "bg-success-500",
  warning: "bg-warning-500",
  danger: "bg-danger-500",
  neutral: "bg-neutral-400",
  info: "bg-info-500",
};

export function StatusDot({ tone = "neutral", pulse = false }: { tone?: StatusTone; pulse?: boolean }) {
  return (
    <span className="relative inline-flex size-2">
      {pulse && (
        <span
          className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", TONE_CLASSES[tone])}
        />
      )}
      <span className={cn("relative inline-flex size-2 rounded-full", TONE_CLASSES[tone])} />
    </span>
  );
}
