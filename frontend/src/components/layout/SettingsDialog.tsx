import { Bell, Bot, Lock, Monitor, Palette } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Dialog } from "../common/Dialog";
import { Switch } from "../common/Switch";
import { Select } from "../common/Input";
import { Badge } from "../common/Badge";
import { cn } from "../../lib/utils";
import { useLocalStorage } from "../../hooks/useLocalStorage";
import { AGENTS } from "../../services/mock/agents";

type SettingsTab = "appearance" | "interface" | "notifications" | "agents" | "security";

const TABS: { id: SettingsTab; label: string; icon: LucideIcon }[] = [
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "interface", label: "Interface", icon: Monitor },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "agents", label: "Agent Preferences", icon: Bot },
  { id: "security", label: "Security", icon: Lock },
];

export function SettingsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [tab, setTab] = useState<SettingsTab>("appearance");
  const [theme, setTheme] = useLocalStorage("settings.theme", "light");
  const [density, setDensity] = useLocalStorage("settings.density", "comfortable");
  const [showTimestamps, setShowTimestamps] = useLocalStorage("settings.showTimestamps", true);
  const [notifyOnComplete, setNotifyOnComplete] = useLocalStorage("settings.notifyOnComplete", false);
  const [soundOnComplete, setSoundOnComplete] = useLocalStorage("settings.soundOnComplete", false);
  const [defaultAgent, setDefaultAgent] = useLocalStorage("settings.defaultAgent", "general");
  const [confirmTools, setConfirmTools] = useLocalStorage("settings.confirmTools", true);

  return (
    <Dialog open={open} onClose={onClose} title="Settings" size="lg">
      <div className="flex min-h-[380px] gap-6">
        <nav className="w-44 shrink-0 space-y-0.5">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors",
                tab === id
                  ? "bg-neutral-150 text-neutral-900 font-medium"
                  : "text-neutral-600 hover:bg-neutral-100",
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              {label}
            </button>
          ))}
        </nav>

        <div className="min-w-0 flex-1 space-y-5">
          {tab === "appearance" && (
            <div className="space-y-4">
              <SettingRow label="Theme" description="Light is fully supported today; Dark and System are in progress.">
                <div className="flex gap-2">
                  {(["light", "dark", "system"] as const).map((option) => (
                    <button
                      key={option}
                      onClick={() => setTheme(option)}
                      disabled={option !== "light"}
                      className={cn(
                        "rounded-md border px-3 py-1.5 text-sm capitalize transition-colors disabled:cursor-not-allowed disabled:opacity-40",
                        theme === option
                          ? "border-neutral-900 bg-neutral-900 text-neutral-0"
                          : "border-neutral-200 text-neutral-700 hover:bg-neutral-50",
                      )}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </SettingRow>
            </div>
          )}

          {tab === "interface" && (
            <div className="space-y-4">
              <SettingRow label="Density" description="Controls spacing in the message list.">
                <div className="flex gap-2">
                  {(["comfortable", "compact"] as const).map((option) => (
                    <button
                      key={option}
                      onClick={() => setDensity(option)}
                      className={cn(
                        "rounded-md border px-3 py-1.5 text-sm capitalize transition-colors",
                        density === option
                          ? "border-neutral-900 bg-neutral-900 text-neutral-0"
                          : "border-neutral-200 text-neutral-700 hover:bg-neutral-50",
                      )}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </SettingRow>
              <SettingRow label="Show timestamps" description="Display the time under each message.">
                <Switch checked={showTimestamps} onChange={setShowTimestamps} label="Show timestamps" />
              </SettingRow>
            </div>
          )}

          {tab === "notifications" && (
            <div className="space-y-4">
              <SettingRow label="Notify when a response completes" description="Requires browser notification permission.">
                <Switch checked={notifyOnComplete} onChange={setNotifyOnComplete} label="Notify on completion" />
              </SettingRow>
              <SettingRow label="Play sound on completion">
                <Switch checked={soundOnComplete} onChange={setSoundOnComplete} label="Sound on completion" />
              </SettingRow>
            </div>
          )}

          {tab === "agents" && (
            <div className="space-y-4">
              <SettingRow label="Default agent" description="Used when starting a new chat.">
                <Select
                  value={defaultAgent}
                  onChange={(e) => setDefaultAgent(e.target.value)}
                  className="w-48"
                >
                  {AGENTS.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </Select>
              </SettingRow>
              <SettingRow label="Confirm before running tools" description="Ask before an agent executes a tool step.">
                <Switch checked={confirmTools} onChange={setConfirmTools} label="Confirm before running tools" />
              </SettingRow>
            </div>
          )}

          {tab === "security" && (
            <div className="space-y-3">
              <Badge tone="neutral">Not yet connected</Badge>
              <p className="text-sm text-neutral-500">
                Single sign-on, session policy, and audit export will appear here once this
                workbench is connected to your organization's identity provider and backend.
              </p>
            </div>
          )}
        </div>
      </div>
    </Dialog>
  );
}

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-neutral-100 pb-4 last:border-0 last:pb-0">
      <div>
        <p className="text-sm font-medium text-neutral-800">{label}</p>
        {description && <p className="mt-0.5 text-sm text-neutral-500">{description}</p>}
      </div>
      {children}
    </div>
  );
}
