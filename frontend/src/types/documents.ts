/** Local knowledge base document metadata (see backend/app/rag/). */
export interface KnowledgeDocument {
  documentId: string;
  filename: string;
  docType: string;
  chunkCount: number;
  ingestedAt: string;
}

export interface DocumentSearchResult {
  chunkId: string;
  documentId: string;
  filename: string;
  pageNumber: number | null;
  text: string;
  score: number;
}
