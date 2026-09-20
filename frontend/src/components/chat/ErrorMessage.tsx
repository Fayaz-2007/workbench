import { AlertCircle } from "lucide-react";

export function ErrorMessage({ text }: { text: string }) {
  return (
    <div className="flex gap-3">
      <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-danger-50">
        <AlertCircle className="size-3.5 text-danger-500" aria-hidden="true" />
      </div>
      <div className="rounded-md border border-danger-500/20 bg-danger-50 px-3.5 py-2.5 text-sm text-danger-600">
        {text}
      </div>
    </div>
  );
}
