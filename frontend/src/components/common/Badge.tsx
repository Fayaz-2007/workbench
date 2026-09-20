import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info" | "accent";

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: "bg-neutral-100 text-neutral-700",
  success: "bg-success-50 text-success-600",
  warning: "bg-warning-50 text-warning-600",
  danger: "bg-danger-50 text-danger-600",
  info: "bg-info-50 text-info-500",
  accent: "bg-accent-50 text-accent-700",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
