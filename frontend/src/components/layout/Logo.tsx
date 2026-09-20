import { ShieldHalf } from "lucide-react";
import { cn } from "../../lib/utils";

export function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2 overflow-hidden">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-neutral-900">
        <ShieldHalf className="size-4.5 text-neutral-0" aria-hidden="true" />
      </div>
      <span
        className={cn(
          "whitespace-nowrap text-[15px] font-semibold leading-tight text-neutral-900 transition-opacity",
          collapsed && "opacity-0",
        )}
      >
        Sovereign AI
        <span className="block text-[11px] font-medium text-neutral-500">Workbench</span>
      </span>
    </div>
  );
}
