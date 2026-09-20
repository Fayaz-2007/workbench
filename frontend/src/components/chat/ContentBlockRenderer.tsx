import { TriangleAlert } from "lucide-react";
import type { ContentBlock } from "../../types";
import { CodeBlock } from "./CodeBlock";
import { MarkdownMessage } from "./MarkdownMessage";

export function ContentBlockRenderer({ block }: { block: ContentBlock }) {
  switch (block.type) {
    case "text":
      return <MarkdownMessage text={block.text} />;
    case "code":
      return <CodeBlock code={block.code} language={block.language} />;
    case "table":
      return <DataTable headers={block.headers} rows={block.rows} />;
    case "warning":
      return (
        <div className="flex items-start gap-2 rounded-md border border-warning-500/30 bg-warning-50 px-3 py-2.5 text-sm text-warning-600">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{block.text}</span>
        </div>
      );
    default:
      return null;
  }
}

function DataTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-neutral-150">
      <table className="w-full text-left text-sm">
        <thead className="bg-neutral-50 text-neutral-500">
          <tr>
            {headers.map((header, i) => (
              <th key={i} className="whitespace-nowrap px-3 py-2 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="whitespace-nowrap px-3 py-2 text-neutral-700">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
