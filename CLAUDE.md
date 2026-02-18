# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paper aggregator that fetches academic papers from journals and Indian institutional sources, stores them in SQLite, and generates a static HTML dashboard. Focused on India-relevant economics, finance, and management research.

## Commands

```bash
# Fetch papers and regenerate dashboard
python3 fetch.py --generate

# Fetch only (no regeneration)
python3 fetch.py
python3 fetch.py --journals-only    # RSS feeds only
python3 fetch.py --sources-only     # Institutional sources only

# Generate dashboard only
python3 generate.py

# Local development server (serves output/)
python3 serve.py                    # Opens http://localhost:8000
python3 serve.py --port 3000        # Custom port
```

## Architecture

### Data Flow
1. `fetch.py` → reads `config.yaml` → calls fetchers in `sources/` → stores in `papers.db` via `db.py`
2. `generate.py` → reads from `db.py` → renders `templates/index.html` via Jinja2 → writes to `output/index.html`

### Source Fetchers (`sources/`)
- `base.py`: `BaseFetcher` ABC and `is_india_relevant()` keyword filter
- `journals.py`: `JournalFetcher` for RSS feeds (feedparser)
- `rbi.py`: RBI, SEBI, NIPFP, NCAER scrapers (BeautifulSoup)
- `thinktanks.py`: ICRIER, CPR, Ashoka, IIMA, IGIDR, ISI Delhi, XKDR, JNU, CSEP, FICCI
- `nber.py`: NBER working papers (India-filtered)
- `unctad.py`: UNCTAD publications (India-filtered)
- `cag.py`: CAG audit reports

All fetchers inherit from `BaseFetcher` and implement `fetch() -> Iterator[Paper]`.

### India Relevance
Papers from non-Indian sources are filtered by `is_india_relevant()` in `sources/base.py`, which matches against keywords (institutions, cities, companies, policies). Sources in `INDIA_SOURCES` set bypass filtering.

## Deployment

- **GitHub Pages**: https://easymanie.github.io/paper-aggregator/
- Auto-deploys on push to `main` via `.github/workflows/deploy.yml`
- Daily paper fetch at 6 AM UTC via `.github/workflows/fetch-papers.yml`

## Database

SQLite at `papers.db`. Schema in `db.py`. Papers deduplicated by URL. Only papers from 2024+ are kept (`CUTOFF_DATE`).
