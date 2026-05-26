import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

export const dynamic = "force-dynamic";

const LEADERBOARD_PATH = process.env.LEADERBOARD_PATH ?? "/leaderboard.md";

type Block = {
  headers: string[];
  rows: string[][];
};

function parseLeaderboard(md: string): Block[] {
  const lines = md.split(/\r?\n/);
  const blocks: Block[] = [];
  let current: Block | null = null;
  let sawSeparator = false;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line.startsWith("|")) {
      if (current && current.rows.length > 0) blocks.push(current);
      current = null;
      sawSeparator = false;
      continue;
    }
    const cells = line.split("|").slice(1, -1).map((s) => s.trim());
    if (cells.length === 0) continue;
    const isSeparator = cells.every((c) => /^-+$/.test(c));
    if (isSeparator) {
      sawSeparator = true;
      continue;
    }
    if (current === null) {
      current = { headers: cells, rows: [] };
      sawSeparator = false;
    } else if (sawSeparator) {
      current.rows.push(cells);
    } else {
      // Two header-like rows in a row would be a malformed block; reset.
      if (current.rows.length > 0) blocks.push(current);
      current = { headers: cells, rows: [] };
    }
  }
  if (current && current.rows.length > 0) blocks.push(current);
  return blocks;
}

function blockTitle(headers: string[]): string {
  const set = new Set(headers);
  if (set.has("recall@10")) return "retrieval (recall + precision)";
  if (set.has("contradiction_f1")) return "contradiction (LLM vs NLI)";
  if (set.has("temporal_consistency")) return "temporal (decay)";
  return "leaderboard";
}

export default async function EvalPage() {
  let md = "";
  let error: string | null = null;
  try {
    md = await readFile(resolve(LEADERBOARD_PATH), "utf-8");
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  const blocks = md ? parseLeaderboard(md) : [];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">eval leaderboard</h1>
        <p className="text-(--muted) text-sm mt-1">
          parsed from <code>{LEADERBOARD_PATH}</code> &middot;{" "}
          {blocks.length} block{blocks.length === 1 ? "" : "s"}
        </p>
      </div>

      {error && (
        <div className="border border-red-700 bg-red-950/30 text-red-300 rounded p-3 text-sm">
          could not read leaderboard.md: {error}
          <div className="text-(--muted) mt-1 text-xs">
            run <code>make eval</code> on the host to produce it; docker-compose mounts
            it into this container.
          </div>
        </div>
      )}

      {blocks.length === 0 && !error && (
        <div className="text-(--muted) text-sm">
          no rows yet. run <code>make eval</code> or <code>make eval-compare</code>.
        </div>
      )}

      {blocks.map((b, i) => (
        <section key={i}>
          <h2 className="text-sm font-semibold text-(--muted) uppercase tracking-wide mb-2">
            {blockTitle(b.headers)}
          </h2>
          <div className="overflow-x-auto border border-(--border) rounded-lg">
            <table className="w-full text-xs">
              <thead className="bg-(--card) border-b border-(--border) text-left text-(--muted)">
                <tr>
                  {b.headers.map((h) => (
                    <th key={h} className="px-2 py-1.5 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {b.rows.map((r, ri) => (
                  <tr key={ri} className="border-b border-(--border) last:border-0">
                    {r.map((c, ci) => (
                      <td key={ci} className="px-2 py-1.5 whitespace-nowrap">
                        {c}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
