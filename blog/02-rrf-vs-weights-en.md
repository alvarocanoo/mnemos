# Why I picked RRF over hand-tuned weights for hybrid retrieval — before I had numbers to prove it

> The first post in this series promised a follow-up that would compare RRF against simpler weighting *on `mnemos-bench-v1`*, with real numbers. This is not that post. The bench has not been run yet — Docker is sulking on my dev box. What I can do honestly today is explain why I picked RRF over a hand-tuned weighting scheme in the first place, *under uncertainty*. The numbers-vs-numbers post lands when the bench runs.

If you want the upstream of this post, the system is at [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos) and the previous post in the series is *"I wrote the eval suite before I wrote the memory system"*.

## The decision I could not postpone

Hybrid retrieval gives you two ranked lists — one from BM25 (lexical), one from dense embeddings (semantic) — and asks you to merge them into one. That merge is a design decision you make *once*, you bake into the storage layer, and you defend in every subsequent conversation about retrieval quality.

When I was sketching the hybrid path for `mnemos`, the bench did not exist yet. (It does now — 75 hand-authored cases across five task types — but it does not have numbers for these two configurations side by side.) I had no per-task data telling me whether dense or sparse would dominate. I had no calibration of either retriever's score distribution on my domain. I had a half-written Qdrant collection config and a deadline.

That is the situation where most "we should measure" advice is useless. You *will* measure, eventually. The question is what defensible default ships today so that future measurements have something to push against.

## The two real options

I narrowed it to two:

**Option A — Weighted average of normalised scores.** Run both retrievers, normalise each to `[0, 1]` (min-max or z-score), combine as `w_dense · s_dense + w_sparse · s_sparse`, sort. The two weights are tunable hyperparameters.

**Option B — Reciprocal Rank Fusion (RRF).** Run both retrievers, ignore the scores entirely, use the *rank* of each document in each list. The fused score of a document `d` is `Σ_i 1 / (k + rank_i(d))` summed across retrievers. Default `k = 60`, the same value the 2009 paper used and the one Qdrant exposes by default. Sort by fused score.

Both are simple to implement. Both are reasonable. They behave differently in two specific ways:

- **Option A is sensitive to score distributions.** Dense cosine similarity sits in roughly `[0, 1]`, BM25 scores can be arbitrarily large depending on corpus stats. Normalising to a common range hides this, but the normalisation choice itself becomes a hyperparameter — and a hidden one, because most teams normalise once and forget about it.
- **Option B is sensitive only to *order*.** It does not care whether the top BM25 hit had score 18.4 or score 4.2. It only cares that it was first. That makes RRF robust to retriever recalibrations: if you swap embedding models or change the BM25 indexer, the fusion does not have to be re-tuned.

## Why hand-tuned weights is a trap for a junior shipping this

I will be blunt because the bias I am fighting is one I share. The weighted average looks more sophisticated. It has knobs. Knobs feel like control. When a recruiter or interviewer asks "how did you pick fusion?", saying *"I tuned w_dense and w_sparse on a held-out set"* sounds like an engineer who understood the problem.

The trap is that to set those weights honestly, you need three things I did not have on day one:

1. A held-out set whose distribution matches production traffic. (My 75-case bench is hand-authored, not production traffic. The weights I'd learn would be weights for *my* taste in queries, not for an unknown future user's.)
2. A scoring metric that the optimiser converges on stably. With small N, even nDCG@10 has high variance run-to-run.
3. A defensible story for *why those specific weights* — not "I gridsearched" but "here is the geometry of my retrieval space that predicts these weights".

Without (1), (2), (3), tuned weights are an overfit to whatever I tried first that looked better. Shipping that and calling it "tuned" is worse than shipping RRF and calling it the default.

RRF has zero domain hyperparameters to tune. `k = 60` is the value the original paper found insensitive to corpus and retriever choices, validated repeatedly since. Picking it is not a decision I owe a domain justification for. It is the *cited default*.

## The defensible claim, in one sentence

> "I picked RRF as the fusion default because it requires no calibration of retriever scores, has a 15-year track record of being robust across IR tasks, and is the implementation Qdrant ships natively — which means I am not maintaining custom fusion code that diverges from upstream over time."

That sentence holds whether the bench numbers turn out flattering or unflattering, because it does not claim RRF is the best on my data. It claims it is the defensible default *under uncertainty*. Future-me will hold past-me to that.

## The implementation, in real code

`mnemos`'s hybrid retrieval lives in two files. The Qdrant layer at [packages/core/mnemos/storage/qdrant.py](https://github.com/alvarocanoo/mnemos/blob/main/packages/core/mnemos/storage/qdrant.py) issues a single `query_points` call with a `Prefetch` per retriever and a `FusionQuery(fusion=Fusion.RRF)` to merge:

```python
def hybrid_search(
    settings: Settings,
    dense_query: list[float],
    sparse_query: SparseVec,
    user_id: str,
    limit: int,
    prefetch_limit: int = 50,
) -> list[tuple[UUID, float]]:
    client = get_client()
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            qm.Prefetch(
                query=dense_query,
                using="dense",
                limit=prefetch_limit,
                filter=_user_filter(user_id),
            ),
            qm.Prefetch(
                query=qm.SparseVector(
                    indices=sparse_query.indices,
                    values=sparse_query.values,
                ),
                using="sparse",
                limit=prefetch_limit,
                filter=_user_filter(user_id),
            ),
        ],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF),
        limit=limit,
        with_payload=False,
    )
    return [(UUID(str(point.id)), float(point.score)) for point in response.points]
```

That is the entire fusion code. No weights. No score normalisation. One call, two prefetches, RRF.

`prefetch_limit = 50` is the only knob worth defending. Qdrant's docs recommend prefetch > limit so fusion has enough material to merge meaningfully. Fifty is a `v0.5` default; tuning it lives in the eval loop, not in a comment.

The retrieval layer at [packages/core/mnemos/retrieval/hybrid.py](https://github.com/alvarocanoo/mnemos/blob/main/packages/core/mnemos/retrieval/hybrid.py) wraps the Qdrant call, joins Postgres metadata, and multiplies the fused score by a temporal decay weight before returning the top-`k`. That decay multiplication is the *only* place `mnemos` modifies a Qdrant score, and it is honest about it — same factor for every memory in the candidate pool, so the rank order only changes when decay weights differ across ages.

## What the leaderboard will say (and what it will not)

When the bench runs, four rows will appear in `leaderboard.md` for the retrieval table:

| config | retriever | fusion | recall@10 |
|---|---|---|---|
| `naive_dense_only` | dense | — | ? |
| `bm25_only` | sparse | — | ? |
| `mnemos_hybrid_no_decay` | dense + sparse | RRF | ? |
| `mnemos_full` | dense + sparse | RRF + decay | ? |

Three readings of those rows would all be useful:

- **Hybrid >> either alone.** RRF is doing real work. The post-#2 essay writes itself.
- **Hybrid ≈ dense alone.** BM25 is contributing little on these 75 cases. Worth examining whether the dataset is too semantic, or whether BM25 is being smothered by the dense top-k.
- **Hybrid < dense alone.** RRF is degrading retrieval. This would be surprising but not unprecedented on small benchmarks; the post would dig into why, probably with per-case dumps.

Note what I am *not* writing: a row called `mnemos_hybrid_weighted`. I did not implement weighted-average fusion because doing so honestly would require me to commit to a tuning protocol — held-out split, optimiser, weight grid — and the dataset is too small to do that without overfitting. If the bench results push toward "RRF was wrong", the next move is to grow the dataset first, then tune.

## What I cannot honestly claim today

To stay inside the rule of this post — no numbers, no claims that need numbers — the things I am *not* saying right now:

- I am not saying RRF beats weighted average on `mnemos-bench-v1`. The bench has not been run for either side.
- I am not saying RRF beats weighted average in general. The 2009 paper says it beats Condorcet and learning-to-rank on TREC-scale data; my data is 75 cases, not TREC.
- I am not claiming `prefetch_limit = 50` is optimal. It is the Qdrant-recommended starting point and I have not swept it.
- I am not claiming BGE-M3 + Qdrant BM25 is the best retriever pair. They are the cheapest defensible pair given the constraint of running locally with no API key.

Those gaps are the agenda of subsequent posts and bench runs, not concealments.

## Next

The next post in this series will compare the LLM-as-judge implementation of contradiction detection against the NLI baseline on the 15 `contradiction` cases in the bench. Same shape: write the design first, run the bench, report the gap honestly. If the LLM judge does not clearly beat the NLI baseline, the post becomes "why I shipped two judges and let users pick". If it does, the post becomes "the cost of being right".

---

*Built as part of the third project of my 2026 AI-engineer portfolio. Repo: [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos). Bilingual source: [English](02-rrf-vs-weights-en.md) · [Spanish](02-rrf-vs-weights-es.md).*
