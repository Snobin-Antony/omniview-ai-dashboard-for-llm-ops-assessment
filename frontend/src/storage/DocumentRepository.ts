/** API-first document repository facade — components must not touch IndexedDB. */
import { api } from "../api";
import type { Document, DocumentList } from "../types";

export const DocumentRepository = {
  list(
    userId: string,
    workspaceId: string,
    filters: {
      status?: string;
      owner_id?: string;
      cursor?: string;
      limit?: string;
    }
  ): Promise<DocumentList> {
    return api.listDocuments(userId, workspaceId, {
      status: filters.status,
      owner_id: filters.owner_id,
      cursor: filters.cursor,
      limit: filters.limit ?? "40",
    });
  },

  get(userId: string, workspaceId: string, documentId: string): Promise<Document> {
    return api.getDocument(userId, workspaceId, documentId);
  },

  analyze(userId: string, workspaceId: string, documentId: string) {
    return api.analyzeDocument(userId, workspaceId, documentId);
  },
};
