export function LoadingMessage() {
  return (
    <div className="flex gap-3">
      <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutral-900">
        <span className="size-2 rounded-full bg-neutral-0 animate-pulse-soft" />
      </div>
      <div className="flex items-center gap-1 pt-2">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 rounded-full bg-neutral-300 animate-pulse-soft"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
