import { Badge } from "../common/Badge";
import { StatusDot } from "../common/StatusDot";
import type { BadgeTone } from "../common/Badge";
import type { ModelStatus } from "../../types";

const TONE_BY_STATUS: Record<ModelStatus, BadgeTone> = {
  active: "success",
  idle: "neutral",
  loading: "info",
  error: "danger",
  disabled: "neutral",
};

const DOT_TONE_BY_STATUS: Record<ModelStatus, "success" | "neutral" | "info" | "danger"> = {
  active: "success",
  idle: "neutral",
  loading: "info",
  error: "danger",
  disabled: "neutral",
};

const LABEL_BY_STATUS: Record<ModelStatus, string> = {
  active: "Active",
  idle: "Idle",
  loading: "Loading",
  error: "Error",
  disabled: "Disabled",
};

export function ModelStatusBadge({ status }: { status: ModelStatus }) {
  return (
    <Badge tone={TONE_BY_STATUS[status]}>
      <StatusDot tone={DOT_TONE_BY_STATUS[status]} pulse={status === "loading"} />
      {LABEL_BY_STATUS[status]}
    </Badge>
  );
}
