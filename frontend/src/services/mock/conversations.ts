import type { ConversationSummary } from "../../types";

export const MOCK_CONVERSATIONS: ConversationSummary[] = [
  {
    id: "conv_1",
    title: "Draft vendor approval note",
    agentId: "document",
    updatedAt: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
  },
  {
    id: "conv_2",
    title: "Refactor ingestion pipeline",
    agentId: "code",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  },
  {
    id: "conv_3",
    title: "Q3 maintenance cost review",
    agentId: "data",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
  },
  {
    id: "conv_4",
    title: "Inspect turbine schematic",
    agentId: "vision",
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
  },
];
