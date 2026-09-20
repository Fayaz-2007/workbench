import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  active?: boolean;
  size?: "sm" | "md";
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { className, label, active, size = "md", children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex items-center justify-center rounded-md text-neutral-600 transition-colors",
        "hover:bg-neutral-100 hover:text-neutral-900",
        "disabled:pointer-events-none disabled:opacity-40",
        size === "md" ? "size-9" : "size-7",
        active && "bg-neutral-150 text-neutral-900",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
});
