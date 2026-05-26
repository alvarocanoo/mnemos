## What

<!-- One sentence: what does this PR change? Why does it exist? -->

## Why this exists

<!-- The user-facing or eval-facing reason. If it touches retrieval / contradiction /
decay / eviction, link to the leaderboard row or per-case JSON that motivated it. -->

## How to verify

- [ ] `uv run pytest -q` is green
- [ ] `uv run ruff check` is clean
- [ ] `uv run ruff format --check` is clean
- [ ] If it touches an eval metric or runner: re-ran `make eval-*` and pasted the
      relevant leaderboard row below (or attached the new `eval-runs/*.json`)

## Notes

<!-- Anything a reviewer should know that isn't obvious from the diff:
     scope cuts taken, alternatives considered, follow-ups deliberately deferred. -->
