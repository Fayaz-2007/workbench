import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "../../lib/utils";
import { IconButton } from "./IconButton";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
}

const SIZE_CLASSES = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

export function Dialog({ open, onClose, title, description, children, footer, size = "md" }: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    panelRef.current?.focus();
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-neutral-950/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        tabIndex={-1}
        className={cn(
          "relative flex max-h-[85vh] w-full flex-col rounded-lg border border-neutral-150 bg-neutral-0 shadow-lg focus:outline-none",
          SIZE_CLASSES[size],
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-neutral-150 px-5 py-4">
          <div>
            <h2 id="dialog-title" className="text-base font-semibold text-neutral-900">
              {title}
            </h2>
            {description && <p className="mt-0.5 text-sm text-neutral-500">{description}</p>}
          </div>
          <IconButton label="Close dialog" onClick={onClose}>
            <X className="size-4" />
          </IconButton>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-neutral-150 px-5 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
