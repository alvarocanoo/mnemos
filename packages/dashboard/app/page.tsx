import Link from "next/link";
import { apiBase, readyz } from "@/lib/api";

type ReadyzShape = {
  postgres?: { ok?: boolean };
  qdrant?: { ok?: boolean };
  collection?: string;
  embedding_model?: string;
};

async function safeReadyz(): Promise<ReadyzShape | { error: string }> {
  try {
    return (await readyz()) as ReadyzShape;
  } catch (err) {
    return { error: err instanceof Error ? err.message : String(err) };
  }
}

const CARDS = [
  {
    href: "/memories",
    title: "memories",
    desc: "Paginated table of stored memories with importance, age, access count.",
  },
  {
    href: "/eval",
    title: "eval",
    desc: "Leaderboard rendered from leaderboard.md — retrieval, contradiction, temporal blocks.",
  },
  {
    href: "/timeline",
    title: "timeline",
    desc: "Memories ranked by composite eviction score; visualises decay weight per importance tier.",
  },
];

export default async function Home() {
  const health = await safeReadyz();
  return (
    <div className="flex flex-col gap-8">
      <section>
        <h1 className="text-3xl font-bold tracking-tight">dashboard</h1>
        <p className="text-(--muted) mt-2 text-sm">
          read-only views over the mnemos service.
        </p>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {CARDS.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="border border-(--border) rounded-lg p-5 bg-(--card) hover:border-(--accent) transition"
          >
            <div className="text-(--accent) text-lg font-semibold">{c.title}</div>
            <div className="text-xs text-(--muted) mt-2 leading-relaxed">{c.desc}</div>
          </Link>
        ))}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-(--muted) uppercase tracking-wide">
          stack health
        </h2>
        <div className="mt-3 border border-(--border) rounded-lg p-4 bg-(--card)">
          <div className="text-xs text-(--muted) mb-2">
            via <code>{apiBase()}/readyz</code>
          </div>
          {"error" in health ? (
            <div className="text-red-400 text-sm">
              service unreachable: {health.error}
            </div>
          ) : (
            <ul className="text-sm space-y-1">
              <li>
                postgres:{" "}
                <span className={health.postgres?.ok ? "text-green-400" : "text-red-400"}>
                  {health.postgres?.ok ? "ok" : "down"}
                </span>
              </li>
              <li>
                qdrant:{" "}
                <span className={health.qdrant?.ok ? "text-green-400" : "text-red-400"}>
                  {health.qdrant?.ok ? "ok" : "down"}
                </span>
              </li>
              <li>
                collection: <code>{health.collection}</code>
              </li>
              <li>
                embedding: <code>{health.embedding_model}</code>
              </li>
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
