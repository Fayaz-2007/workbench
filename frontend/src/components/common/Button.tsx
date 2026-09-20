import { Loader2 } from "lucide-react";
import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-neutral-900 text-neutral-0 hover:bg-neutral-800 active:bg-neutral-900 disabled:bg-neutral-300",
  secondary:
    "bg-neutral-0 text-neutral-800 border border-neutral-200 hover:bg-neutral-50 active:bg-neutral-100 disabled:text-neutral-400",
  ghost:
    "bg-transparent text-neutral-700 hover:bg-neutral-100 active:bg-neutral-150 disabled:text-neutral-400",
  danger:
    "bg-danger-500 text-neutral-0 hover:bg-danger-600 active:bg-danger-600 disabled:bg-neutral-300",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", size = "md", loading, disabled, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors",
        "disabled:cursor-not-allowed",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
});
