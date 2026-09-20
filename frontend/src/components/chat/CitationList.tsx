import { Link2 } from "lucide-react";
import type { Citation } from "../../types";

/** Distinct chunks of the same document (no page number to tell them apart)
 * produce identical labels — collapse those down to one badge per label so
 * a multi-chunk match doesn't show "file.md" twice.
 */
function dedupeByLabel(citations: Citation[]): Citation[] {
  const seen = new Set<string>();
  return citations.filter((c) => {
    if (seen.has(c.label)) return false;
    seen.add(c.label);
    return true;
  });
}

export function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {dedupeByLabel(citations).map((citation) => (
        <span
          key={citation.id}
          title={citation.source}
          className="inline-flex items-center gap-1 rounded-full border border-neutral-150 bg-neutral-0 px-2 py-1 text-xs text-neutral-500"
        >
          <Link2 className="size-3" aria-hidden="true" />
          {citation.label}
        </span>
      ))}
    </div>
  );
}
