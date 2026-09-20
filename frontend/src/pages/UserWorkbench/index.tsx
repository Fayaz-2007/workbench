import { Sidebar } from "../../components/layout/Sidebar";
import { ChatHeader } from "../../components/layout/ChatHeader";
import { MessageList } from "../../components/chat/MessageList";
import { WelcomeState } from "../../components/chat/WelcomeState";
import { Composer } from "../../components/chat/Composer";
import { useWorkbench } from "../../context/WorkbenchContext";
import { useAttachments } from "../../hooks/useAttachments";
import { useLocalStorage } from "../../hooks/useLocalStorage";
import { useState } from "react";
import { getAgentDisplay } from "../../services/mock/agents";

export function UserWorkbench() {
  const {
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
  } = useWorkbench();

  const [sidebarCollapsed, setSidebarCollapsed] = useLocalStorage("ui.sidebarCollapsed", false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { attachments, addFiles, removeAttachment, clearAttachments } = useAttachments();

  const agent = getAgentDisplay(selectedAgentId)!;
  const hasMessages = messages.length > 0;

  const handleSend = (text: string) => {
    sendMessage(text, attachments);
    clearAttachments();
  };

  const handleNewChat = () => {
    startNewConversation();
    setMobileMenuOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    openConversation(id);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-neutral-0">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        conversations={conversations}
        conversationsLoading={conversationsLoading}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          agent={agent}
          canSwitchAgent={!hasMessages}
          onSelectAgent={selectAgent}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
        />

        <div className="flex flex-1 flex-col overflow-y-auto">
          {hasMessages ? (
            <MessageList messages={messages} isSending={isSending} />
          ) : (
            <WelcomeState selectedAgentId={selectedAgentId} onSelectAgent={selectAgent} />
          )}
        </div>

        <Composer
          agentId={selectedAgentId}
          attachments={attachments}
          isSending={isSending}
          onAddFiles={addFiles}
          onRemoveAttachment={removeAttachment}
          onSend={handleSend}
        />
      </div>
    </div>
  );
}
