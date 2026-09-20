import { BookOpen, CircleHelp, PanelLeftClose, PanelLeftOpen, Plus, Settings, X } from "lucide-react";
import { useState } from "react";
import { IconButton } from "../common/IconButton";
import { cn, formatRelativeTime } from "../../lib/utils";
import type { ConversationSummary } from "../../types";
import { getAnyAgentDisplay } from "../../services/mock/agents";
import { Logo } from "./Logo";
import { UserMenu } from "./UserMenu";
import { SettingsDialog } from "./SettingsDialog";
import { AboutDialog } from "./AboutDialog";
import { KnowledgeBaseDialog } from "./KnowledgeBaseDialog";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  conversations: ConversationSummary[];
  conversationsLoading: boolean;
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  conversations,
  conversationsLoading,
  activeConversationId,
  onSelectConversation,
  onNewChat,
}: SidebarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [knowledgeBaseOpen, setKnowledgeBaseOpen] = useState(false);

  const content = (
    <div className="flex h-full flex-col bg-neutral-25">
      <div className="flex h-14 shrink-0 items-center justify-between gap-2 px-3">
        <Logo collapsed={collapsed} />
        <IconButton
          label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={onToggleCollapse}
          className="hidden md:inline-flex"
        >
          {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
        </IconButton>
        <IconButton label="Close menu" onClick={onCloseMobile} className="md:hidden">
          <X className="size-4" />
        </IconButton>
      </div>

      <div className="px-3">
        <button
          onClick={onNewChat}
          aria-label="New chat"
          title={collapsed ? "New chat" : undefined}
          className={cn(
            "flex h-10 w-full items-center gap-2 rounded-md border border-neutral-200 bg-neutral-0 px-3 text-sm font-medium text-neutral-800 shadow-xs transition-colors hover:bg-neutral-50",
            collapsed && "justify-center px-0",
          )}
        >
          <Plus className="size-4 shrink-0" aria-hidden="true" />
          {!collapsed && "New chat"}
        </button>
        <button
          onClick={() => setKnowledgeBaseOpen(true)}
          aria-label="Knowledge Base"
          title={collapsed ? "Knowledge Base" : undefined}
          className={cn(
            "mt-1.5 flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900",
            collapsed && "justify-center px-0",
          )}
        >
          <BookOpen className="size-4 shrink-0" aria-hidden="true" />
          {!collapsed && "Knowledge Base"}
        </button>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto px-3 pb-3">
        {!collapsed && (
          <p className="px-1 pb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
            Recent
          </p>
        )}
        {conversationsLoading ? (
          <div className="space-y-1.5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-9 animate-pulse rounded-md bg-neutral-100" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          !collapsed && <p className="px-1 py-2 text-sm text-neutral-400">No conversations yet</p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map((conversation) => {
              const agent = getAnyAgentDisplay(conversation.agentId);
              const Icon = agent?.icon;
              const active = conversation.id === activeConversationId;
              return (
                <li key={conversation.id}>
                  <button
                    onClick={() => onSelectConversation(conversation.id)}
                    title={conversation.title}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm transition-colors",
                      active ? "bg-neutral-150 text-neutral-900" : "text-neutral-600 hover:bg-neutral-100",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    {Icon && <Icon className="size-4 shrink-0 text-neutral-500" aria-hidden="true" />}
                    {!collapsed && (
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate">{conversation.title}</span>
                        <span className="text-xs text-neutral-400">
                          {formatRelativeTime(conversation.updatedAt)}
                        </span>
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="shrink-0 space-y-1 border-t border-neutral-150 px-3 py-3">
        <UserMenu collapsed={collapsed} />
        <button
          onClick={() => setSettingsOpen(true)}
          aria-label="Settings"
          title={collapsed ? "Settings" : undefined}
          className={cn(
            "flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900",
            collapsed && "justify-center px-0",
          )}
        >
          <Settings className="size-4 shrink-0" aria-hidden="true" />
          {!collapsed && "Settings"}
        </button>
        <button
          onClick={() => setAboutOpen(true)}
          aria-label="Help & About"
          title={collapsed ? "Help & About" : undefined}
          className={cn(
            "flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900",
            collapsed && "justify-center px-0",
          )}
        >
          <CircleHelp className="size-4 shrink-0" aria-hidden="true" />
          {!collapsed && "Help & About"}
        </button>
      </div>

      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <AboutDialog open={aboutOpen} onClose={() => setAboutOpen(false)} />
      <KnowledgeBaseDialog open={knowledgeBaseOpen} onClose={() => setKnowledgeBaseOpen(false)} />
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden shrink-0 border-r border-neutral-150 transition-[width] duration-200 md:block",
          collapsed ? "w-16" : "w-64",
        )}
      >
        {content}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-neutral-950/40" onClick={onCloseMobile} aria-hidden="true" />
          <aside className="relative z-10 h-full w-72 max-w-[85vw] border-r border-neutral-150 bg-neutral-25 shadow-lg">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
