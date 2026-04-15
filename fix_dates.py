#!/usr/bin/env python3
"""One-time script to backfill missing dates in the papers database.

Strategies:
1. IGIDR papers: Re-scrape IDEAS/RePEc and match by URL to get year from headings
2. ISI Delhi papers: Same strategy as IGIDR
3. Journal papers (IIMB Management Review etc): Re-parse RSS feeds to get dates
4. Think tank papers: Extract year from URL patterns or title text
"""

import re
import sqlite3
import sys
from pathlib import Path

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

DB_PATH = Path(__file__).parent / "papers.db"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_papers_missing_dates(source=None):
    """Get papers with no published_date."""
    conn = get_connection()
    cursor = conn.cursor()
    if source:
        cursor.execute(
            "SELECT id, url, title, source FROM papers WHERE published_date IS NULL AND source = ?",
            (source,)
        )
    else:
        cursor.execute(
            "SELECT id, url, title, source FROM papers WHERE published_date IS NULL"
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def update_date(paper_id, date_str):
    """Update a paper's published_date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE papers SET published_date = ? WHERE id = ?", (date_str, paper_id))
    conn.commit()
    conn.close()


def fix_repec_dates(source_name, repec_url, link_pattern):
    """Fix dates for papers from IDEAS/RePEc by parsing year headings."""
    papers = get_papers_missing_dates(source_name)
    if not papers:
        print(f"  {source_name}: No papers with missing dates")
        return 0

    print(f"  {source_name}: {len(papers)} papers missing dates, fetching from {repec_url}...")

    try:
        response = requests.get(repec_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  Error fetching {repec_url}: {e}")
        return 0

    soup = BeautifulSoup(response.content, 'lxml')

    # Build URL -> year mapping from the page
    url_to_year = {}
    current_year = None

    # Parse both h3 (series pages) and h4 (department pages) year headings
    for elem in soup.find_all(['h3', 'h4', 'li']):
        if elem.name in ('h3', 'h4'):
            year_text = elem.get_text(strip=True)
            if year_text.isdigit():
                current_year = int(year_text)
            else:
                current_year = None
            continue

        if not current_year:
            continue

        link = elem.find('a', href=lambda h: h and link_pattern in str(h))
        if link:
            href = link.get('href', '')
            full_url = f"https://ideas.repec.org{href}" if href.startswith('/') else href
            url_to_year[full_url] = current_year

    # Match and update
    fixed = 0
    for paper in papers:
        if paper['url'] in url_to_year:
            year = url_to_year[paper['url']]
            update_date(paper['id'], f"{year}-01-01")
            fixed += 1

    print(f"  {source_name}: Fixed {fixed}/{len(papers)} dates")
    return fixed


def fix_journal_dates():
    """Fix dates for journal papers by re-parsing RSS feeds."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    journals = config.get("journals", [])
    total_fixed = 0

    for journal in journals:
        name = journal.get("name", "")
        url = journal.get("url", "")

        papers = get_papers_missing_dates(name)
        if not papers:
            continue

        print(f"  {name}: {len(papers)} papers missing dates, re-parsing RSS...")

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  Error parsing {name} feed: {e}")
            continue

        # Build URL -> date mapping from feed
        url_to_date = {}
        for entry in feed.entries:
            entry_url = entry.get('link', '')
            if not entry_url:
                continue

            # Try multiple date fields
            date_str = None
            for date_field in ['published_parsed', 'updated_parsed']:
                parsed = entry.get(date_field)
                if parsed:
                    try:
                        date_str = f"{parsed.tm_year}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
                        break
                    except:
                        pass

            if not date_str:
                # Try string date fields
                for field in ['published', 'updated', 'dc_date']:
                    raw = entry.get(field, '')
                    if raw:
                        # Try to extract YYYY-MM-DD
                        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', raw)
                        if match:
                            date_str = match.group(0)
                            break

            if date_str:
                url_to_date[entry_url] = date_str

        # Match papers by URL
        fixed = 0
        for paper in papers:
            paper_url = paper['url']
            if paper_url in url_to_date:
                update_date(paper['id'], url_to_date[paper_url])
                fixed += 1
            else:
                # Try matching by DOI or partial URL
                for feed_url, date in url_to_date.items():
                    # Extract DOI from both and compare
                    doi_match = re.search(r'(10\.\d+/\S+)', paper_url)
                    feed_doi_match = re.search(r'(10\.\d+/\S+)', feed_url)
                    if doi_match and feed_doi_match and doi_match.group(1) == feed_doi_match.group(1):
                        update_date(paper['id'], date)
                        fixed += 1
                        break

        if fixed:
            print(f"  {name}: Fixed {fixed}/{len(papers)} dates")
        total_fixed += fixed

    return total_fixed


def fix_url_year_dates():
    """Fix dates by extracting year from URL patterns for remaining papers."""
    papers = get_papers_missing_dates()
    if not papers:
        print("  No papers with missing dates remaining")
        return 0

    print(f"  Attempting to extract dates from URLs for {len(papers)} papers...")

    fixed = 0
    for paper in papers:
        url = paper['url']
        title = paper['title']
        date_str = None

        # Try year from URL path segments like /2024/ or /2025/
        year_match = re.search(r'/(202[4-9])/', url)
        if year_match:
            date_str = f"{year_match.group(1)}-01-01"

        # Try YYYY-MM pattern in URL
        if not date_str:
            ym_match = re.search(r'/(202[4-9])[-/](\d{2})/', url)
            if ym_match:
                date_str = f"{ym_match.group(1)}-{ym_match.group(2)}-01"

        # Try year from title
        if not date_str:
            title_year = re.search(r'\b(202[4-9])\b', title)
            if title_year:
                date_str = f"{title_year.group(1)}-01-01"

        if date_str:
            update_date(paper['id'], date_str)
            fixed += 1

    print(f"  Fixed {fixed}/{len(papers)} dates from URLs/titles")
    return fixed


def main():
    print("=" * 50)
    print("Paper Date Backfill Script")
    print("=" * 50)

    # Show current state
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM papers WHERE published_date IS NULL")
    missing = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM papers")
    total = cursor.fetchone()[0]
    print(f"\nPapers with missing dates: {missing}/{total}")

    if missing == 0:
        print("No papers need date fixes!")
        return

    # Show breakdown by source
    cursor.execute("""
        SELECT source, COUNT(*) as cnt
        FROM papers WHERE published_date IS NULL
        GROUP BY source ORDER BY cnt DESC
    """)
    print("\nBreakdown by source:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    conn.close()

    total_fixed = 0

    # 1. Fix IGIDR papers via IDEAS/RePEc year headings
    print("\n--- Fixing IGIDR dates (IDEAS/RePEc) ---")
    total_fixed += fix_repec_dates("IGIDR", "https://ideas.repec.org/s/ind/igiwpp.html", "/p/ind/igiwpp/")

    # 2. Fix ISI Delhi papers via IDEAS/RePEc year headings
    print("\n--- Fixing ISI Delhi dates (IDEAS/RePEc) ---")
    total_fixed += fix_repec_dates("ISI Delhi", "https://ideas.repec.org/s/alo/isipdp.html", "/p/alo/isipdp/")

    # 3. Fix journal paper dates via RSS feeds
    print("\n--- Fixing journal dates (RSS feeds) ---")
    total_fixed += fix_journal_dates()

    # 4. Fix remaining papers by URL/title year extraction
    print("\n--- Fixing remaining dates (URL/title patterns) ---")
    total_fixed += fix_url_year_dates()

    # Summary
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM papers WHERE published_date IS NULL")
    still_missing = cursor.fetchone()[0]
    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Fixed {total_fixed} paper dates")
    print(f"Still missing: {still_missing}/{total}")


if __name__ == "__main__":
    main()
