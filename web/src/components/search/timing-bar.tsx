"use client";

interface TimingBarProps {
  timings: Record<string, number>;
}

const COLORS: Record<string, string> = {
  embed_query_ms: "bg-blue-500",
  retrieval_ms: "bg-green-500",
  rerank_ms: "bg-amber-500",
};

export function TimingBar({ timings }: TimingBarProps) {
  const entries = Object.entries(timings);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  if (total === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Timing breakdown</span>
        <span>{total.toFixed(0)} ms total</span>
      </div>
      <div className="flex h-4 overflow-hidden rounded-full bg-muted">
        {entries.map(([key, value]) => {
          const pct = (value / total) * 100;
          if (pct < 0.5) return null;
          return (
            <div
              key={key}
              className={`${COLORS[key] || "bg-gray-400"} flex items-center justify-center text-[9px] font-medium text-white`}
              style={{ width: `${pct}%` }}
              title={`${key}: ${value.toFixed(1)} ms`}
            >
              {pct > 15 ? key.replace("_ms", "") : ""}
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {entries.map(([key, value]) => (
          <span key={key}>
            {key}: {value.toFixed(1)} ms
          </span>
        ))}
      </div>
    </div>
  );
}
