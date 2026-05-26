import { scoreEviction, type ScoreItem } from "@/lib/api";

function importanceColor(level: number): string {
  if (level >= 3) return "bg-amber-500";
  if (level === 2) return "bg-sky-500";
  return "bg-zinc-500";
}

export default async function TimelinePage({
  searchParams,
}: {
  searchParams: Promise<{ user_id?: string }>;
}) {
  const params = await searchParams;
  const userId = params.user_id ?? "default";

  let items: ScoreItem[] = [];
  let error: string | null = null;
  try {
    items = await scoreEviction(userId);
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  // Bars are normalised against the highest score in the current view so the
  // visualisation is always usable; the score column shows the raw value.
  const maxScore = items.reduce((m, x) => Math.max(m, x.score), 1);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">timeline / decay</h1>
        <p className="text-(--muted) text-sm mt-1">
          user_id: <code>{userId}</code> &middot; bars normalised against the max score in
          this view. lower score = more likely to be evicted.
        </p>
      </div>

      {error && (
        <div className="border border-red-700 bg-red-950/30 text-red-300 rounded p-3 text-sm">
          {error}
        </div>
      )}

      <div className="border border-(--border) rounded-lg overflow-hidden">
        <div className="grid grid-cols-12 text-xs uppercase tracking-wide text-(--muted) bg-(--card) border-b border-(--border) px-3 py-2">
          <div className="col-span-1">imp</div>
          <div className="col-span-2">age</div>
          <div className="col-span-2">recency w</div>
          <div className="col-span-1 text-right">acc</div>
          <div className="col-span-2 text-right">score</div>
          <div className="col-span-4">bar</div>
        </div>
        {items.length === 0 && !error && (
          <div className="px-3 py-6 text-center text-sm text-(--muted)">
            no scored memories for this user
          </div>
        )}
        {items.map((it) => {
          const widthPct = Math.max(2, (it.score / maxScore) * 100);
          return (
            <div
              key={it.memory_id}
              className="grid grid-cols-12 items-center text-xs px-3 py-2 border-b border-(--border) last:border-0"
            >
              <div className="col-span-1">{it.importance}</div>
              <div className="col-span-2 text-(--muted)">{it.age_days.toFixed(1)}d</div>
              <div className="col-span-2 text-(--muted)">
                {it.recency_weight.toFixed(3)}
              </div>
              <div className="col-span-1 text-right text-(--muted)">
                {it.access_count}
              </div>
              <div className="col-span-2 text-right font-mono">
                {it.score.toFixed(3)}
              </div>
              <div className="col-span-4">
                <div className="w-full bg-(--border) rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full ${importanceColor(it.importance)}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
