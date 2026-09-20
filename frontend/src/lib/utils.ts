type ClassValue = string | number | false | null | undefined | Record<string, boolean>;

/** Minimal class-name combiner — avoids pulling in clsx/tailwind-merge. */
export function cn(...values: ClassValue[]): string {
  const out: string[] = [];
  for (const value of values) {
    if (!value) continue;
    if (typeof value === "string" || typeof value === "number") {
      out.push(String(value));
    } else {
      for (const key in value) {
        if (value[key]) out.push(key);
      }
    }
  }
  return out.join(" ");
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** exponent;
  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHour = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

let idCounter = 0;

/** Simple unique id generator for frontend-only mock entities. */
export function generateId(prefix = "id"): string {
  idCounter += 1;
  return `${prefix}_${Date.now().toString(36)}_${idCounter}`;
}

const EXTENSION_LABELS: Record<string, string> = {
  pdf: "PDF Document",
  docx: "Word Document",
  doc: "Word Document",
  xlsx: "Excel Spreadsheet",
  xls: "Excel Spreadsheet",
  csv: "CSV File",
  pptx: "PowerPoint Presentation",
  ppt: "PowerPoint Presentation",
  png: "PNG Image",
  jpg: "JPEG Image",
  jpeg: "JPEG Image",
  txt: "Text File",
  py: "Python Script",
  cpp: "C++ Source",
  c: "C Source",
  js: "JavaScript File",
  ts: "TypeScript File",
};

export function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

export function getFileTypeLabel(filename: string): string {
  const ext = getFileExtension(filename);
  return EXTENSION_LABELS[ext] ?? (ext ? `${ext.toUpperCase()} File` : "File");
}
