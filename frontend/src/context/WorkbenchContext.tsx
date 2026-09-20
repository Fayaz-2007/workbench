import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import * as api from "../services/api/client";
import type { AgentSelection, ChatAttachment, ChatMessage, ConversationSummary } from "../types";
import { generateId } from "../lib/utils";
import { toAgentSelection } from "../services/mock/agents";

interface WorkbenchState {
  selectedAgentId: AgentSelection;
  selectAgent: (id: AgentSelection) => void;

  conversations: ConversationSummary[];
  conversationsLoading: boolean;

  activeConversationId: string | null;
  messages: ChatMessage[];
  isSending: boolean;

  startNewConversation: () => void;
  openConversation: (id: string) => Promise<void>;
  sendMessage: (text: string, attachments: ChatAttachment[]) => Promise<void>;
}

const WorkbenchContext = createContext<WorkbenchState | null>(null);

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [selectedAgentId, setSelectedAgentId] = useState<AgentSelection>("general");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);

  const refreshConversations = useCallback(async () => {
    setConversationsLoading(true);
    try {
      const list = await api.getConversations();
      setConversations(list);
    } finally {
      setConversationsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const selectAgent = useCallback((id: AgentSelection) => {
    setSelectedAgentId(id);
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
  }, []);

  const openConversation = useCallback(async (id: string) => {
    const conversation = await api.getConversation(id);
    if (!conversation) return;
    setActiveConversationId(conversation.id);
    setSelectedAgentId(toAgentSelection(conversation.agentId));
    setMessages(conversation.messages);
  }, []);

  const sendMessage = useCallback(
    async (text: string, attachments: ChatAttachment[]) => {
      if (!text.trim() && attachments.length === 0) return;

      let conversationId = activeConversationId;
      if (!conversationId) {
        // Auto mode: seed the conversation record with a placeholder —
        // sendMessage() below updates it to the agent actually resolved
        // by the Task Router once the response comes back.
        const conversation = api.createConversation(selectedAgentId === "auto" ? "general" : selectedAgentId);
        conversationId = conversation.id;
        setActiveConversationId(conversationId);
      }

      const userMessage: ChatMessage = {
        id: generateId("msg"),
        role: "user",
        status: "complete",
        createdAt: new Date().toISOString(),
        text,
        attachments,
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);

      try {
        const assistantMessage = await api.sendMessage({
          conversationId,
          agentId: selectedAgentId,
          text,
          attachments,
        });
        setMessages((prev) => [...prev, assistantMessage]);
        await refreshConversations();
      } catch (error) {
        const errorMessage: ChatMessage = {
          id: generateId("msg"),
          role: "assistant",
          status: "error",
          createdAt: new Date().toISOString(),
          agentId: selectedAgentId === "auto" ? undefined : selectedAgentId,
          errorMessage: error instanceof Error ? error.message : "Something went wrong.",
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsSending(false);
      }
    },
    [activeConversationId, selectedAgentId, refreshConversations],
  );

  const value = useMemo<WorkbenchState>(
    () => ({
      selectedAgentId,
      selectAgent,
      conversations,
      conversationsLoading,
      activeConversationId,
      messages,
      isSending,
      startNewConversation,
      openConversation,
      sendMessage,
    }),
    [
      selectedAgentId,
      selectAgent,
      conversations,
      conversationsLoading,
      activeConversationId,
      messages,
      isSending,
      startNewConversation,
      openConversation,
      sendMessage,
    ],
  );

  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

export function useWorkbench(): WorkbenchState {
  const ctx = useContext(WorkbenchContext);
  if (!ctx) throw new Error("useWorkbench must be used within a WorkbenchProvider");
  return ctx;
}
