"""Database operations for the paper aggregator."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


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
    limit: int = 500,
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

    query += " ORDER BY published_date DESC, fetched_date DESC LIMIT ?"
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
