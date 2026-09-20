import { Info } from "lucide-react";

export function SystemMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-center">
      <div className="flex items-center gap-1.5 rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-500">
        <Info className="size-3.5" aria-hidden="true" />
        {text}
      </div>
    </div>
  );
}
