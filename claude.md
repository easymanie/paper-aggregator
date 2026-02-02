# Paper Aggregator - Session Notes

## Project Overview
Python-based paper aggregator that fetches academic papers from journals and institutional sources, stores them in SQLite, and generates a static HTML dashboard.

## Key Files
- `fetch.py` - Fetches papers from configured sources
- `generate.py` - Generates HTML output
- `db.py` - Database operations
- `config.yaml` - Source configuration
- `papers.db` - SQLite database (gitignored)
- `output/index.html` - Generated dashboard

## Commands

**Fetch new papers and regenerate:**
```bash
cd ~/Downloads/paper-aggregator
python3 fetch.py
python3 generate.py
```

**Run local server:**
```bash
python3 serve.py
# Opens at http://localhost:8000
```

**Push to GitHub:**
```bash
git add -A
git commit -m "Your message"
git push
```

## GitHub Setup
- **Repo**: https://github.com/easymanie/paper-aggregator
- **Branch**: `main`
- **Auth**: Fine-grained PAT with Contents read/write permission

## GitHub Action
Automated daily fetch configured in `.github/workflows/fetch-papers.yml`:
- **Schedule**: Daily at 6 AM UTC (11:30 AM IST)
- **Manual trigger**: Actions → Fetch Papers → Run workflow
- Auto-commits and pushes if new papers found

## Netlify Deployment
- **Publish directory**: `output`
- **Build command**: (empty - HTML is pre-generated)
- Link to GitHub for auto-deploy on push

### Linking Netlify to GitHub:
1. Netlify dashboard → Site configuration → Build & deploy
2. Link to Git → GitHub → `easymanie/paper-aggregator`
3. Branch: `main`, Publish directory: `output`

## Sources
- 47 journal RSS feeds
- 15 institutional sources (RBI, NIPFP, NCAER, ICRIER, CPR, NBER, etc.)
- Some sources disabled: SEBI, SSRN, Kiel Institute, Twitter/X
