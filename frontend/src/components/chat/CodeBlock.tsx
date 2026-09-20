import { Check, Copy } from "lucide-react";
import { useState } from "react";

export function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable — silently ignore.
    }
  };

  return (
    <div className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-900">
      <div className="flex items-center justify-between px-3 py-1.5">
        <span className="text-xs font-medium text-neutral-400">{language || "text"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-1.5 py-1 text-xs text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-neutral-100"
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto px-3 pb-3 text-sm leading-relaxed">
        <code className="font-mono text-neutral-100">{code}</code>
      </pre>
    </div>
  );
}
