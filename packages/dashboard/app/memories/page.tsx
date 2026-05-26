import { listMemories, type Memory } from "@/lib/api";

function daysAgo(iso: string): number {
  const t = new Date(iso).getTime();
  return Math.max(0, (Date.now() - t) / 86_400_000);
}

function importanceBadge(level: number) {
  const map = {
    1: "bg-zinc-700 text-zinc-200",
    2: "bg-sky-700 text-sky-100",
    3: "bg-amber-600 text-amber-50",
  } as const;
  const label = level === 1 ? "low" : level === 3 ? "high" : "normal";
  const cls = map[level as 1 | 2 | 3] ?? map[2];
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {label}
    </span>
  );
}

export default async function MemoriesPage({
  searchParams,
}: {
  searchParams: Promise<{ user_id?: string }>;
}) {
  const params = await searchParams;
  const userId = params.user_id ?? "default";

  let memories: Memory[] = [];
  let error: string | null = null;
  try {
    memories = await listMemories(userId, 100);
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">memories</h1>
        <p className="text-(--muted) text-sm mt-1">
          user_id: <code>{userId}</code> &middot; showing up to 100, newest first
        </p>
      </div>

      {error && (
        <div className="border border-red-700 bg-red-950/30 text-red-300 rounded p-3 text-sm">
          {error}
        </div>
      )}

      <div className="overflow-x-auto border border-(--border) rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-(--card) border-b border-(--border) text-left text-xs uppercase tracking-wide text-(--muted)">
            <tr>
              <th className="px-3 py-2">imp</th>
              <th className="px-3 py-2">content</th>
              <th className="px-3 py-2 text-right">age</th>
              <th className="px-3 py-2 text-right">access</th>
              <th className="px-3 py-2">user</th>
            </tr>
          </thead>
          <tbody>
            {memories.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-(--muted)">
                  no memories
                </td>
              </tr>
            )}
            {memories.map((m) => (
              <tr key={m.id} className="border-b border-(--border) last:border-0">
                <td className="px-3 py-2">{importanceBadge(m.importance)}</td>
                <td className="px-3 py-2 max-w-xl">{m.content}</td>
                <td className="px-3 py-2 text-right text-(--muted) whitespace-nowrap">
                  {daysAgo(m.created_at).toFixed(1)}d
                </td>
                <td className="px-3 py-2 text-right text-(--muted)">{m.access_count}</td>
                <td className="px-3 py-2 text-(--muted)">{m.user_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
