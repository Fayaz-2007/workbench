import { cn } from "../../lib/utils";

export function Switch({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5.5 w-9.5 shrink-0 items-center rounded-full transition-colors",
        checked ? "bg-neutral-900" : "bg-neutral-200",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span
        className={cn(
          "inline-block size-4 transform rounded-full bg-neutral-0 shadow-sm transition-transform",
          checked ? "translate-x-4.5" : "translate-x-1",
        )}
      />
    </button>
  );
}
