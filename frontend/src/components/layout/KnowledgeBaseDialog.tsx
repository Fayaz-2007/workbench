import { AlertCircle, FileText, Search, Trash2, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Dialog } from "../common/Dialog";
import { Button } from "../common/Button";
import { Badge } from "../common/Badge";
import { EmptyState } from "../common/EmptyState";
import { Input } from "../common/Input";
import { formatTimestamp } from "../../lib/utils";
import {
  deleteKnowledgeDocument,
  ingestKnowledgeDocument,
  listKnowledgeDocuments,
  searchKnowledgeBase,
  uploadFile,
} from "../../services/api/client";
import type { DocumentSearchResult, KnowledgeDocument } from "../../types";

const INGEST_EXTENSIONS = ".pdf,.docx,.txt,.md,.csv,.xlsx,.png,.jpg,.jpeg";

export function KnowledgeBaseDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [documents, setDocuments] = useState<KnowledgeDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = () =>
    listKnowledgeDocuments()
      .then((docs) => {
        setDocuments(docs);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load documents."));

  useEffect(() => {
    if (open) refresh();
  }, [open]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadFile(file);
      await ingestKnowledgeDocument(uploaded.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    try {
      await deleteKnowledgeDocument(documentId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove document.");
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const results = await searchKnowledgeBase(query.trim());
      setSearchResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  };

  const totalChunks = documents?.reduce((sum, d) => sum + d.chunkCount, 0) ?? 0;

  return (
    <Dialog open={open} onClose={onClose} title="Knowledge Base" description="Local documents used by the Document Agent's RAG search." size="lg">
      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-md border border-neutral-150 bg-neutral-25 px-3 py-2">
          <div className="flex items-center gap-4 text-sm text-neutral-600">
            <span>{documents?.length ?? "…"} document(s)</span>
            <span>{totalChunks} chunk(s) indexed</span>
          </div>
          <Badge tone="success">LOCAL DATA</Badge>
        </div>

        {error && (
          <p className="flex items-center gap-1.5 text-sm text-danger-500">
            <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}

        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept={INGEST_EXTENSIONS}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleUpload(file);
              e.target.value = "";
            }}
          />
          <Button variant="secondary" loading={uploading} onClick={() => fileInputRef.current?.click()}>
            <UploadCloud className="size-4" aria-hidden="true" />
            Upload & index document
          </Button>
        </div>

        <div className="flex gap-2">
          <Input
            placeholder="Search indexed documents…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <Button variant="secondary" loading={searching} onClick={handleSearch}>
            <Search className="size-4" aria-hidden="true" />
            Search
          </Button>
        </div>

        {searchResults && (
          <div className="space-y-2 rounded-md border border-neutral-150 p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">
              {searchResults.length} result(s)
            </p>
            {searchResults.length === 0 ? (
              <p className="text-sm text-neutral-500">No relevant passages found.</p>
            ) : (
              searchResults.map((r) => (
                <div key={r.chunkId} className="rounded-md bg-neutral-25 p-2.5 text-sm">
                  <p className="mb-1 flex items-center justify-between text-xs text-neutral-400">
                    <span>
                      {r.filename}
                      {r.pageNumber ? ` (p.${r.pageNumber})` : ""}
                    </span>
                    <span>{r.score.toFixed(2)}</span>
                  </p>
                  <p className="line-clamp-3 text-neutral-700">{r.text}</p>
                </div>
              ))
            )}
          </div>
        )}

        <div className="max-h-72 overflow-y-auto rounded-md border border-neutral-150">
          {documents === null ? (
            <p className="p-4 text-sm text-neutral-400">Loading…</p>
          ) : documents.length === 0 ? (
            <EmptyState icon={FileText} title="No documents indexed yet" description="Upload a document to make it searchable by the Document Agent." />
          ) : (
            <ul className="divide-y divide-neutral-100">
              {documents.map((doc) => (
                <li key={doc.documentId} className="flex items-center justify-between gap-3 px-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-neutral-800">{doc.filename}</p>
                    <p className="text-xs text-neutral-400">
                      {doc.docType.toUpperCase()} · {doc.chunkCount} chunk(s) · {formatTimestamp(doc.ingestedAt)}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.documentId)}
                    aria-label={`Remove ${doc.filename}`}
                    className="flex size-8 shrink-0 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-danger-50 hover:text-danger-500"
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <p className="text-xs text-neutral-400">
          Documents, embeddings, and search all run on this server — nothing is sent to an external service.
        </p>
      </div>
    </Dialog>
  );
}
