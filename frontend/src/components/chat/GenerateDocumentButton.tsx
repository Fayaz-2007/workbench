import { AlertCircle, FileSpreadsheet, FileText, Presentation as PresentationIcon, X } from "lucide-react";
import { useState } from "react";
import { Button } from "../common/Button";
import { Dropdown } from "../common/Dropdown";
import { DeliverableCard } from "../deliverables/DeliverableCard";
import { ExecutionSteps } from "../execution/ExecutionSteps";
import { exportConversation } from "../../services/api/client";
import type { ChatMessage, Deliverable, ExecutionStep, ExportFormat } from "../../types";

const FORMAT_OPTIONS: { format: ExportFormat; label: string }[] = [
  { format: "docx", label: "Word (.docx)" },
  { format: "pptx", label: "PowerPoint (.pptx)" },
  { format: "xlsx", label: "Excel (.xlsx)" },
  { format: "pdf", label: "PDF" },
];

/** "Generate Document" — the button-triggered path for the same
 * conversation-export pipeline the natural-language chat trigger uses
 * (see backend/app/services/conversation_export and
 * `docs`: "generate a document about this" in the composer). Calls
 * `POST /api/conversations/{id}/export` directly rather than going through
 * `/api/chat`, since this isn't a chat turn.
 */
export function GenerateDocumentButton({
  conversationId,
  messages,
}: {
  conversationId: string | null;
  messages: ChatMessage[];
}) {
  const [loading, setLoading] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<ExecutionStep[] | null>(null);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);

  const disabled = !conversationId || messages.length === 0;

  const handleGenerate = async (format: ExportFormat) => {
    if (!conversationId) return;
    setLoading(format);
    setError(null);
    setSteps(null);
    setDeliverable(null);
    try {
      const result = await exportConversation(conversationId, format, messages);
      setSteps(result.executionSteps);
      setDeliverable(result.deliverable);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document generation failed.");
    } finally {
      setLoading(null);
    }
  };

  const reset = () => {
    setSteps(null);
    setDeliverable(null);
    setError(null);
  };

  if (deliverable) {
    return (
      <div className="mb-2 space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-neutral-500">Generated document</p>
          <button
            type="button"
            onClick={reset}
            aria-label="Dismiss"
            className="text-neutral-400 hover:text-neutral-600"
          >
            <X className="size-3.5" aria-hidden="true" />
          </button>
        </div>
        {steps && steps.length > 0 && <ExecutionSteps steps={steps} />}
        <DeliverableCard deliverable={deliverable} />
      </div>
    );
  }

  return (
    <div className="mb-2">
      <Dropdown
        align="start"
        trigger={
          <Button size="sm" variant="secondary" disabled={disabled || loading !== null} loading={loading !== null}>
            <FileText className="size-3.5" aria-hidden="true" />
            Generate Document
          </Button>
        }
        items={FORMAT_OPTIONS.map((option) => ({
          id: option.format,
          label: option.label,
          icon: <FormatIcon format={option.format} />,
          onSelect: () => handleGenerate(option.format),
        }))}
      />
      {error && (
        <p className="mt-1.5 flex items-center gap-1.5 text-xs text-danger-500">
          <AlertCircle className="size-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}

function FormatIcon({ format }: { format: ExportFormat }) {
  if (format === "pptx") return <PresentationIcon className="size-3.5" aria-hidden="true" />;
  if (format === "xlsx") return <FileSpreadsheet className="size-3.5" aria-hidden="true" />;
  return <FileText className="size-3.5" aria-hidden="true" />;
}
