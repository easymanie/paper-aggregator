# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paper aggregator that fetches academic papers from journals and Indian institutional sources, stores them in SQLite, and generates a static HTML dashboard. Focused on India-relevant economics, finance, and management research. Deployed to GitHub Pages at https://easymanie.github.io/paper-aggregator/.

## Commands

```bash
# Fetch papers and regenerate dashboard
python3 fetch.py --generate

# Fetch only (no regeneration)
python3 fetch.py
python3 fetch.py --journals-only    # RSS feeds only
python3 fetch.py --sources-only     # Institutional scrapers only

# Generate dashboard only
python3 generate.py

# Local development server (serves output/)
python3 serve.py                    # http://localhost:8000
python3 serve.py --port 3000

# One-time utility: backfill missing published_date values
python3 fix_dates.py
```

## Architecture

### Data flow
1. `fetch.py` → reads `config.yaml` → instantiates fetchers from `sources/` → each yields `Paper` objects → `db.insert_paper` canonicalizes URL + rejects pre-2024 rows + deduplicates via `UNIQUE(url)`.
2. After all fetchers run, `fetch.py` calls `db.cleanup_old_papers`, `cleanup_duplicates`, `cleanup_non_papers`, and `recanonicalize_urls` in sequence.
3. `generate.py` → `db.get_all_papers(limit=None)` → enriches each paper with topic classification, relevance score, daily-brief score, open-access flag, and a Google-search `fallback_url` for closed-access links → renders `templates/index.html` via Jinja2 → writes `output/index.html`. Scores and topics are computed at render time, never stored.

### Source fetchers (`sources/`)
All fetchers subclass `BaseFetcher` and implement `fetch() -> Iterator[Paper]`. `BaseFetcher.should_include` auto-passes papers from India-native sources (`INDIA_SOURCES` set in `base.py`) and runs `is_india_relevant` keyword matching on everything else.

Fetcher files are split by origin:
- `journals.py` — all RSS-based journal feeds via `JournalFetcher`
- `rbi.py` — RBI, SEBI, NIPFP, NCAER
- `thinktanks.py` — ICRIER, CPR, Ashoka CEDA, IIMA, IGIDR, ISI Delhi, XKDR, JNU, CSEP, FICCI, Azim Premji CSE, RIS
- `thinktanks2.py` — ORF, Carnegie India, EPW (added after `thinktanks.py` grew too large)
- `international.py` — IMF, World Bank, ADB
- `nber.py`, `unctad.py`, `cag.py`, `ssrn.py`, `kiel.py`, `twitter.py` — one source per file

`sources/__init__.py` is the canonical export list; `fetch.py` wires each config-named source to its fetcher class via a dict.

### URL canonicalization and deduplication
`db.canonicalize_url` is the single source of truth for URL normalization: strips tracking params (`dgcid`, `utm_*`, `fromrss`, etc.), rewrites sciencedirect PII variants, collapses EPW issue-prefixed paths, and prefers `doi.org/` for any URL with an embedded DOI. It runs on every insert and during `recanonicalize_urls` for historical rows.

`cleanup_duplicates` matches on canonical URL AND fuzzy (source, normalized-title, published_date) AND EPW normalized-title — necessary because the same paper gets posted at multiple URLs. `cleanup_non_papers` drops known landing-page titles like "Research & Publications" and EPW `Vol. X, Issue No. Y` index entries.

`URL_OVERRIDES_BY_TITLE` in `db.py` lets you pin a better URL for specific paper titles that consistently resolve to unusable publisher pages.

### Scoring (generate.py)
- `classify_topic` — tags each paper with one or more of ~12 topic labels based on keyword presence.
- `calculate_relevance_score` — high/medium/low keyword tiers + category/source bonuses.
- `calculate_daily_brief_score` — different scoring tuned for Zerodha's Daily Brief newsletter; imports `get_coverage_penalty` and `is_topic_covered` from `daily_brief_coverage.py` to down-weight topics the Daily Brief has already written about. Update `COVERED_TOPICS` in `daily_brief_coverage.py` as new stories ship.
- `calculate_daily_brief_fit_score` — second fit-oriented score for the same purpose.

### Database
SQLite at `papers.db` — **tracked in git** (not gitignored), so every CI run starts from the accumulated baseline instead of a cold fetch. Without this the deployed site would only show whatever was currently in RSS feeds (~500-600 papers). Schema in `db.py` (11 columns, `url` is `UNIQUE`, indexed on source/date/category). `CUTOFF_DATE = 2024-01-01` is enforced at insert time.

## Deployment

Two workflows in `.github/workflows/`:

- `fetch-papers.yml` — scheduled daily at 6 AM UTC (and `workflow_dispatch`). Fetches, regenerates, commits `papers.db` + `output/index.html`, **and deploys GitHub Pages directly**. The direct Pages deploy is intentional: pushes made with `GITHUB_TOKEN` don't trigger other workflows, so `deploy.yml` wouldn't fire for auto-fetch commits.
- `deploy.yml` — push-triggered Pages deploy. Effectively only runs for manual human pushes to `main`; the fetch workflow bypasses it.

## Operational notes

- If the CI fetch starts producing 0 new papers across the board, check first whether `papers.db` is still tracked. A cold fetch of ~500 papers is the failure signature of `papers.db` having been re-gitignored.
- The `JNU` fetcher falls back from `ideas.repec.org` to `jnu.ac.in` automatically when RePEc 404s — the fallback is conservative and may yield nothing, which is expected.
- Expect occasional ICRIER / RIS timeouts; the fetcher logs and continues. Not a reason to change anything.
