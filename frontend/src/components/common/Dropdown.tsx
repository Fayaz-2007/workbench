import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

export interface DropdownItem {
  id: string;
  label: string;
  icon?: ReactNode;
  onSelect: () => void;
  destructive?: boolean;
}

export function Dropdown({
  trigger,
  items,
  align = "start",
}: {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: "start" | "end";
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative inline-block">
      <div onClick={() => setOpen((v) => !v)}>{trigger}</div>
      {open && (
        <div
          role="menu"
          className={cn(
            "absolute z-40 mt-1 min-w-[180px] rounded-md border border-neutral-150 bg-neutral-0 py-1 shadow-md",
            align === "end" ? "right-0" : "left-0",
          )}
        >
          {items.map((item) => (
            <button
              key={item.id}
              role="menuitem"
              onClick={() => {
                item.onSelect();
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-neutral-50",
                item.destructive ? "text-danger-500" : "text-neutral-700",
              )}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
