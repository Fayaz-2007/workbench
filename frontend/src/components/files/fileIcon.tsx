import {
  FileArchive,
  FileCode2,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Presentation,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getFileExtension } from "../../lib/utils";

const CODE_EXTENSIONS = new Set(["py", "cpp", "c", "js", "ts"]);
const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg"]);

export function getFileIcon(filename: string): LucideIcon {
  const ext = getFileExtension(filename);
  if (IMAGE_EXTENSIONS.has(ext)) return ImageIcon;
  if (CODE_EXTENSIONS.has(ext)) return FileCode2;
  if (ext === "xlsx" || ext === "csv") return FileSpreadsheet;
  if (ext === "pptx") return Presentation;
  if (ext === "pdf" || ext === "docx" || ext === "txt") return FileText;
  return FileArchive;
}
