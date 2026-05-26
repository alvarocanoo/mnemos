# I wrote the eval suite before I wrote the memory system

> Designing `mnemos-bench-v1` first turned out to be the cheapest design decision of the project.

The first time I sat down to start `mnemos`, I had a Postgres schema half-drafted in a side window, a Next.js dashboard mockup in another, and a vague plan to add "an eval thing later". Almost a full afternoon went into deciding which embedding model to default to before I caught myself: I was about to spend three weeks building a memory system whose quality I would judge by *vibes* on a five-memory toy example.

I closed every tab except the blank JSONL file.

This post is about why I started from the eval suite instead, what `mnemos-bench-v1` looks like, and the specific design decisions I would have gotten wrong if I had postponed it.

## What `mnemos` is, in one paragraph

`mnemos` is an agent memory system: an HTTP service that stores short pieces of text ("memories") and lets an agent query them later. The interesting parts are hybrid retrieval (BM25 + dense embeddings + RRF fusion), contradiction detection between memories, temporal decay so old facts fade, and importance-weighted eviction so the database does not grow forever. The whole thing runs locally with `docker compose up`. The full code is at [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos).

The point of this post is not the system. The point is the eval suite I built first, on a blank `*.jsonl` file, before any of the rest existed.

## Why eval-first, concretely

There is a moralising version of "test-first" that sounds like a coding bootcamp poster. That is not what I mean. I mean three specific things I noticed by trying it both ways on smaller projects:

**1. The eval forces the contract.** The moment you write a single test case for "the agent asks a question, the memory system returns the right memories", you have to commit to what a memory looks like (one string? structured?), what a query is (text? embedding?), what counts as a "right" answer (one gold id? top-k overlap?), and what the system returns (a list of ids? hits with scores?). All four are decisions you will make implicitly anyway. Writing them as a test case forces them to the surface before you have a thousand lines of code that assume the wrong shape.

**2. The eval makes scope creep visible.** When you have a numeric target ("recall@10 >= 0.80 on 75 cases") it is hard to lie to yourself about whether a new feature actually helps. Without one, every feature looks like a good idea because everything in isolation is a good idea.

**3. The eval is the first artefact a reviewer reads.** If someone clones your repo and runs `make eval`, the first interaction they have with your work is a number against a dataset. Nothing else you wrote is read until they decide that interaction was honest.

## What `mnemos-bench-v1` actually looks like

The benchmark is 75 cases across five task types. One file per type, all concatenated into a `mnemos_bench_v1.jsonl` artefact. Each line is one JSON object.

The simplest task type is `single_hop_recall`:

```json
{
  "id": "shr_001",
  "task_type": "single_hop_recall",
  "version": "seed_v0",
  "memories": [
    {"content": "The Q3 marketing budget is 450,000 EUR for digital channels.", "importance": 3},
    {"content": "The product team meets every Tuesday at 10am CET.", "importance": 2},
    {"content": "Our primary CRM is Pipedrive and the dashboard owner is Marta.", "importance": 2},
    {"content": "Office address: Calle Mayor 12, Madrid 28013.", "importance": 1},
    {"content": "All employee laptops must be encrypted with FileVault or BitLocker.", "importance": 3}
  ],
  "query": "How much money do we have for Q3 marketing?",
  "gold": {"memory_indices": [0]}
}
```

A handful of memories are ingested, the query is sent, and the metric checks whether the gold memory came back in the top-k. `recall@k = |gold ∩ top_k| / |gold|`. No magic, but the structure forces five specific decisions you cannot avoid:

- Memories carry `importance` (1, 2, 3). Why? Because if you wait to add it later, every downstream module already assumes uniform memories and the refactor is painful. Eviction and temporal decay both need it on day one.
- Gold is `memory_indices` (ints into the case's own `memories[]`), not UUIDs. The runner ingests, gets back the real UUIDs, and translates. This means the dataset is portable across runs — no UUIDs baked in.
- Cases are isolated by `user_id = f"bench_{case.id}"`. The retrieval call filters on `user_id`, so one case's memories do not leak into another's top-k. This made the runner state-free; no per-case database resets, no flakiness.

Compare against `abstention`:

```json
{
  "id": "abs_001",
  "task_type": "abstention",
  "memories": [
    {"content": "Our primary CRM is Pipedrive.", "importance": 2},
    {"content": "GDPR DPO is Carla Morena.", "importance": 3},
    {"content": "Office wifi password rotates quarterly.", "importance": 1}
  ],
  "query": "What is our email marketing platform?",
  "gold": {"memory_indices": [], "expected_empty": true}
}
```

The schema is *the same shape* — same `memories[]`, same `gold.memory_indices` — and `gold.memory_indices = []` is the truth: nothing should be returned. The metric is "did the system return an empty list?". The trick is that the system does have to *want* to abstain, because by default a vector search will always return *something*. I added an optional `score_threshold` parameter to the search endpoint specifically so the agent can ask "give me hits, but only if they pass this bar". Filling that gap was visible *because of the abstention case*; without it I would have shipped a system that confidently returns the closest noisy match to questions it cannot answer.

`temporal_update` cases force the same kind of design pressure. The memory pool has both a `current` and a `superseded` memory for the same fact, plus distractors. The query asks for the fact. The metric is whether the *current* memory ranks above the *superseded* one in top-5. This required the runner to be able to inject `created_at` at ingest time, which became an explicit optional field on `MemoryWrite`. In production this field stays `None` and the database default wins; in eval it lets us simulate aged memories.

`contradiction` is its own shape — pairs of `memory_a` / `memory_b` plus a gold verdict in `{contradicts, supersedes, independent, paraphrase}` — because it tests a different subsystem entirely.

`multi_session_reasoning` reuses the `single_hop_recall` shape but `gold.memory_indices` has 1–2 entries and the query is constructed so it cannot be answered from a single one.

That is the entire schema. ~75 lines of JSON describe what the system has to do.

## The reproducibility constraint

One of the few non-negotiables I gave myself at the start: the eval has to run from a fresh clone in one command. Not "install these tools, set this env, populate the database". Not a notebook. One command.

The reason is selfish. The artefact I want to point a hiring manager at is *not* a screenshot of a leaderboard. It is the experience of:

```powershell
git clone https://github.com/alvarocanoo/mnemos.git
cd mnemos
make sync
make up
make eval-compare
Get-Content leaderboard.md
```

That sequence finishes with a markdown table appended to `leaderboard.md`. If any step requires a brain, the artefact is broken.

To make that work, every eval row records the git SHA of the commit it ran on, the embedding model id (pinned in env), the LLM judge model id when applicable, the dataset filename, and the count of cases. A leaderboard row that does not record what produced it is a leaderboard row I do not trust.

## What did not survive eval-first design

Honest section. Designing the eval first cut two ideas I had been excited about.

The first was a **graph database for entities**. I had been planning to ingest each memory through an entity extractor, write the entities to Neo4j, and use the graph for retrieval. The eval forced me to ask: which test case is this for? `single_hop` does not need it. `multi_session_reasoning` is more about semantic linking than entity overlap. Even `contradiction` benefits more from an LLM judge than from a graph traversal. So I cut the graph. Entities live in a Postgres table — joined when needed, no graph DB to defend in interview.

The second was a **bespoke fusion algorithm**. RRF (Reciprocal Rank Fusion) is famous and free in Qdrant; I had a draft of a "learned" weighting scheme I thought would be more interesting. The eval told me how I would prove it was better: side-by-side rows in the leaderboard, one for RRF, one for the learned scheme. I realised I would not be able to ship the learned scheme in v0.5 *and* defend it in interview *and* get useful numbers from 75 cases. So I shipped RRF and left the learned scheme as a v2 candidate documented in `ARCHITECTURE.md`. Saying no to the shiny idea was a direct gift from having the eval there to refuse it.

## What I will report when the numbers land

This is the part I have not done yet, and saying so is part of the design. The README points to a "Results — pending the first real run" section with the leaderboard's *structure* and explicit `?` cells. The system runs, the tests pass (71 of them), but I have not yet executed the full bench on real hardware. Two blog posts in the planned series depend on those numbers: post #2 on whether RRF actually beats simpler weighting on these 75 cases, and post #4 on what value of the decay lambda performs best on `temporal_update`.

When I write those posts, the headline of each will be the gap between two configurations — RRF vs dense-only; LLM judge vs NLI baseline; decay off vs on — rather than "my system got X%". Those gaps are what the eval framework is built to measure, and they are what I think actually generalises beyond the 75 cases.

## If you want to try it

The repo is at [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos). The dataset is at `packages/eval/mnemos_eval/datasets/mnemos_bench_v1.jsonl` and the per-task `gold` shapes are documented at `packages/eval/mnemos_eval/datasets/schema.md`. The runner code is small enough to read in one sitting — under 200 lines per task type, mostly `httpx` calls into the service plus a metric function.

If you are evaluating this for an AI Engineer role: the part I am most interested in defending is the dataset format and the decisions it forced. The system is a means to make those decisions visible. The next post will compare a baseline configuration to the full one on `mnemos-bench-v1` and report the gap honestly, with the per-case JSON dumped alongside so the misses are inspectable. If the gap is small, that is the post. If the gap is large, that is the post too.

---

*Built as the third project of my 2026 AI-engineer portfolio. Bilingual source: [English](01-eval-first-en.md) · [Spanish](01-eval-first-es.md).*
