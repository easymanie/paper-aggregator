"""Database operations for the paper aggregator."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


# Only keep papers from 2024 onwards
CUTOFF_DATE = "2024-01-01"


@dataclass
class Paper:
    """Represents an academic paper."""
    title: str
    authors: str
    abstract: str
    url: str
    source: str
    category: str
    published_date: Optional[str] = None
    fetched_date: Optional[str] = None
    is_india_specific: bool = True
    is_global_important: bool = False
    id: Optional[int] = None


DB_PATH = Path(__file__).parent / "papers.db"
URL_OVERRIDES_BY_TITLE = {
    "monetary policy transmission bank market power and wholesale funding reliance":
        "https://ideas.repec.org/p/bca/bocawp/23-35.html",
    "the innovation channel of monetary policy and credit supply shocks on firm investment evidence from r d intensive firms in india":
        "https://eurekamag.com/research/104/973/104973748.php",
}


def canonicalize_url(url: str) -> str:
    """Normalize URLs so the same paper does not get inserted repeatedly."""
    if not url:
        return url

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    params_to_remove = {
        "dgcid", "af", "ai", "mi", "ui", "rss", "utm_source", "utm_medium",
        "utm_campaign", "utm_content", "utm_term", "fromrss"
    }
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {
        key: value for key, value in query_params.items()
        if key.lower() not in params_to_remove
    }
    query = urlencode(filtered, doseq=True) if filtered else ""

    if netloc.endswith("epw.in"):
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 5 and parts[0] == "journal" and parts[1].isdigit() and parts[2].isdigit():
            path = "/" + "/".join([parts[0]] + parts[3:])

    if netloc.endswith("sciencedirect.com"):
        pii_match = re.match(r"^/science/article/(?:abs/)?pii/(S\d+)$", path, re.IGNORECASE)
        if pii_match:
            path = f"/science/article/abs/pii/{pii_match.group(1)}"

    # Prefer DOI URLs for publisher landing pages when the DOI is present in the path.
    doi_match = re.search(r"(10\.\d{4,}/[^/?#]+)", path, re.IGNORECASE)
    if netloc.endswith("doi.org") and path.startswith("/"):
        return f"https://doi.org{path}"
    if doi_match:
        doi = doi_match.group(1).rstrip(").,;")
        return f"https://doi.org/{doi}"

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def normalize_title(title: str) -> str:
    """Generate a fuzzy title key for duplicate detection."""
    if not title:
        return ""
    normalized = title.lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = " ".join(normalized.split())
    return normalized


def override_url_for_title(title: str, url: str) -> str:
    """Use curated fallbacks when a publisher URL is consistently unusable."""
    return URL_OVERRIDES_BY_TITLE.get(normalize_title(title), url)


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT,
            abstract TEXT,
            url TEXT UNIQUE,
            source TEXT,
            category TEXT,
            published_date DATE,
            fetched_date DATE,
            is_india_specific BOOLEAN DEFAULT 1,
            is_global_important BOOLEAN DEFAULT 0
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON papers(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON papers(published_date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON papers(category)")

    conn.commit()
    conn.close()


def insert_paper(paper: Paper) -> bool:
    """
    Insert a paper into the database.
    Returns True if inserted, False if already exists (duplicate URL).
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        paper.url = override_url_for_title(paper.title, canonicalize_url(paper.url))

        if paper.published_date and paper.published_date < CUTOFF_DATE:
            return False

        cursor.execute("""
            INSERT INTO papers (
                title, authors, abstract, url, source, category,
                published_date, fetched_date, is_india_specific, is_global_important
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper.title,
            paper.authors,
            paper.abstract,
            paper.url,
            paper.source,
            paper.category,
            paper.published_date,
            paper.fetched_date or datetime.now().strftime("%Y-%m-%d"),
            paper.is_india_specific,
            paper.is_global_important
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Duplicate URL
        return False
    finally:
        conn.close()


def get_all_papers(
    source: Optional[str] = None,
    category: Optional[str] = None,
    india_only: bool = False,
    limit: Optional[int] = None,
    recent_only: bool = True
) -> list[dict]:
    """Get papers with optional filtering."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM papers WHERE 1=1"
    params = []

    # Filter to recent papers (last 3 years)
    if recent_only:
        query += " AND (published_date >= ? OR published_date IS NULL)"
        params.append(CUTOFF_DATE)

    if source:
        query += " AND source = ?"
        params.append(source)

    if category:
        query += " AND category = ?"
        params.append(category)

    if india_only:
        query += " AND (is_india_specific = 1 OR is_global_important = 1)"

    query += " ORDER BY published_date DESC, fetched_date DESC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def cleanup_old_papers():
    """Remove papers older than 3 years."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM papers
        WHERE published_date IS NOT NULL AND published_date < ?
    """, (CUTOFF_DATE,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted


def cleanup_duplicates() -> int:
    """Remove duplicate rows caused by alternate URLs and repeated source imports."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, source, url, published_date FROM papers ORDER BY id DESC")
    rows = cursor.fetchall()

    seen = {}
    duplicate_ids = []

    for row in rows:
        canonical_url = canonicalize_url(row["url"])
        title_key = normalize_title(row["title"])
        published_date = row["published_date"] or ""

        keys = [("url", canonical_url)]
        if published_date:
            keys.append(("title_date", row["source"], title_key, published_date))
        if row["source"] == "EPW":
            keys.append(("epw_title", title_key))

        if any(key in seen for key in keys):
            duplicate_ids.append(row["id"])
        else:
            for key in keys:
                seen[key] = row["id"]

    if duplicate_ids:
        cursor.executemany("DELETE FROM papers WHERE id = ?", [(paper_id,) for paper_id in duplicate_ids])

    deleted = len(duplicate_ids)
    conn.commit()
    conn.close()
    return deleted


def cleanup_non_papers() -> int:
    """Remove generic landing pages and issue indexes that are not papers."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM papers
        WHERE
            lower(trim(title)) IN ('research & publications', 'university connect')
            OR (source = 'EPW' AND lower(title) LIKE 'vol. %, issue no.%')
    """)

    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def recanonicalize_urls() -> int:
    """Rewrite stored URLs to the latest canonical form."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url FROM papers")

    updates = []
    for row in cursor.fetchall():
        canonical_url = override_url_for_title(row["title"], canonicalize_url(row["url"]))
        if canonical_url != row["url"]:
            updates.append((canonical_url, row["id"]))

    if updates:
        cursor.executemany("UPDATE papers SET url = ? WHERE id = ?", updates)

    updated = len(updates)
    conn.commit()
    conn.close()
    return updated


def get_sources() -> list[str]:
    """Get list of unique sources."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT source FROM papers ORDER BY source")
    sources = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sources


def get_categories() -> list[str]:
    """Get list of unique categories."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM papers WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories


def get_paper_count() -> int:
    """Get total number of papers."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM papers")
    count = cursor.fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print(f"Database initialized at {DB_PATH}")
