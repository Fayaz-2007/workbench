import type { ReactNode } from "react";
import { CodeBlock } from "./CodeBlock";

/**
 * Minimal markdown renderer covering the subset agent responses commonly
 * use: paragraphs, headings, lists, bold/italic/inline code, and fenced
 * code blocks. Intentionally dependency-free to keep the bundle light.
 */
export function MarkdownMessage({ text }: { text: string }) {
  const blocks = splitFencedBlocks(text);

  return (
    <div className="space-y-3 text-sm leading-relaxed text-neutral-800">
      {blocks.map((block, i) =>
        block.type === "code" ? (
          <CodeBlock key={i} code={block.code} language={block.language} />
        ) : (
          <div key={i} className="space-y-2">
            {renderTextBlock(block.text)}
          </div>
        ),
      )}
    </div>
  );
}

type Block = { type: "code"; code: string; language?: string } | { type: "text"; text: string };

function splitFencedBlocks(input: string): Block[] {
  const parts = input.split(/```(\w*)\n([\s\S]*?)```/g);
  const blocks: Block[] = [];
  for (let i = 0; i < parts.length; i += 3) {
    const text = parts[i];
    if (text?.trim()) blocks.push({ type: "text", text });
    const language = parts[i + 1];
    const code = parts[i + 2];
    if (code !== undefined) blocks.push({ type: "code", code: code.replace(/\n$/, ""), language });
  }
  return blocks.length > 0 ? blocks : [{ type: "text", text: input }];
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  const parts = text.split(pattern);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={key} className="font-semibold text-neutral-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={key} className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-[0.85em] text-neutral-800">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 1) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

/** True for a GFM table's separator row, e.g. `|---|:--:|---|`. */
function isTableRule(line: string): boolean {
  return /^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(line);
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function renderTextBlock(text: string): ReactNode[] {
  const lines = text.split("\n");
  const nodes: ReactNode[] = [];
  let listBuffer: string[] = [];
  let listKey = 0;
  let tableKey = 0;

  const flushList = () => {
    if (listBuffer.length === 0) return;
    nodes.push(
      <ul key={`ul-${listKey++}`} className="list-disc space-y-1 pl-5">
        {listBuffer.map((item, i) => (
          <li key={i}>{renderInline(item, `li-${listKey}-${i}`)}</li>
        ))}
      </ul>,
    );
    listBuffer = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (!trimmed) {
      flushList();
      continue;
    }

    // A GFM table: a `| a | b |` header row immediately followed by a
    // `|---|---|` rule row. Consume rows until a blank/non-table line.
    if (trimmed.includes("|") && i + 1 < lines.length && isTableRule(lines[i + 1].trim())) {
      flushList();
      const headers = splitTableRow(trimmed);
      const rows: string[][] = [];
      let j = i + 2;
      while (j < lines.length && lines[j].trim().includes("|")) {
        rows.push(splitTableRow(lines[j]));
        j++;
      }
      nodes.push(
        <div key={`table-${tableKey++}`} className="overflow-x-auto rounded-md border border-neutral-150">
          <table className="w-full text-left text-sm">
            <thead className="bg-neutral-50 text-neutral-500">
              <tr>
                {headers.map((header, h) => (
                  <th key={h} className="whitespace-nowrap px-3 py-2 font-medium">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c} className="whitespace-nowrap px-3 py-2 text-neutral-700">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      i = j - 1;
      continue;
    }

    const heading = /^(#{1,3})\s+(.*)/.exec(trimmed);
    if (heading) {
      flushList();
      const level = heading[1].length;
      const className =
        level === 1
          ? "text-base font-semibold text-neutral-900"
          : level === 2
            ? "text-sm font-semibold text-neutral-900"
            : "text-sm font-medium text-neutral-800";
      nodes.push(
        <p key={`h-${i}`} className={className}>
          {renderInline(heading[2], `h-${i}`)}
        </p>,
      );
      continue;
    }

    const listItem = /^[-*]\s+(.*)/.exec(trimmed);
    if (listItem) {
      listBuffer.push(listItem[1]);
      continue;
    }

    flushList();
    nodes.push(<p key={`p-${i}`}>{renderInline(trimmed, `p-${i}`)}</p>);
  }

  flushList();
  return nodes;
}
