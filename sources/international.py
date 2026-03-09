"""Fetchers for international organizations (India-filtered)."""

import re
import requests
from bs4 import BeautifulSoup
from typing import Iterator
from db import Paper
from .base import BaseFetcher
from .thinktanks import HEADERS, parse_date_flexible, is_recent


class IMFFetcher(BaseFetcher):
    """Fetcher for IMF Working Papers via IDEAS/RePEc."""

    PAPERS_URL = "https://ideas.repec.org/s/imf/imfwpa.html"

    def __init__(self):
        super().__init__("IMF", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch IMF working papers from IDEAS/RePEc, filtering for India relevance."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()
            current_year = None

            # IDEAS/RePEc uses h3 for year headings on series pages
            for elem in soup.find_all(['h3', 'li']):
                if elem.name == 'h3':
                    year_text = elem.get_text(strip=True)
                    if year_text.isdigit():
                        current_year = int(year_text)
                    else:
                        current_year = None
                    continue

                if not current_year or current_year < 2024:
                    continue

                link = elem.find('a', href=lambda h: h and '/p/imf/imfwpa/' in str(h))
                if not link:
                    continue

                title = link.get_text(strip=True)
                href = link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue

                seen_urls.add(href)
                url = f"https://ideas.repec.org{href}" if href.startswith('/') else href
                date_text = f"{current_year}-01-01"

                # Extract authors
                text = elem.get_text()
                authors = "IMF"
                author_match = re.search(r'by\s+(.+?)(?:\s*\(|\s*$)', text, re.IGNORECASE)
                if author_match:
                    authors = author_match.group(1).strip() or "IMF"

                paper = Paper(
                    title=title,
                    authors=authors,
                    abstract=f"IMF Working Paper: {title}",
                    url=url,
                    source="IMF",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=False
                )

                if self.should_include(paper):
                    yield paper

        except Exception as e:
            print(f"  Error fetching IMF papers: {e}")


class WorldBankFetcher(BaseFetcher):
    """Fetcher for World Bank Policy Research Working Papers via IDEAS/RePEc."""

    PAPERS_URL = "https://ideas.repec.org/s/wbk/wbrwps.html"

    def __init__(self):
        super().__init__("World Bank", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch World Bank working papers from IDEAS/RePEc, filtering for India relevance."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()
            current_year = None

            # IDEAS/RePEc uses h3 for year headings on series pages
            for elem in soup.find_all(['h3', 'li']):
                if elem.name == 'h3':
                    year_text = elem.get_text(strip=True)
                    if year_text.isdigit():
                        current_year = int(year_text)
                    else:
                        current_year = None
                    continue

                if not current_year or current_year < 2024:
                    continue

                link = elem.find('a', href=lambda h: h and '/p/wbk/wbrwps/' in str(h))
                if not link:
                    continue

                title = link.get_text(strip=True)
                href = link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue

                seen_urls.add(href)
                url = f"https://ideas.repec.org{href}" if href.startswith('/') else href
                date_text = f"{current_year}-01-01"

                text = elem.get_text()
                authors = "World Bank"
                author_match = re.search(r'by\s+(.+?)(?:\s*\(|\s*$)', text, re.IGNORECASE)
                if author_match:
                    authors = author_match.group(1).strip() or "World Bank"

                paper = Paper(
                    title=title,
                    authors=authors,
                    abstract=f"World Bank Policy Research Working Paper: {title}",
                    url=url,
                    source="World Bank",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=False
                )

                if self.should_include(paper):
                    yield paper

        except Exception as e:
            print(f"  Error fetching World Bank papers: {e}")


class ADBFetcher(BaseFetcher):
    """Fetcher for ADB South Asia Working Papers."""

    PAPERS_URL = "https://www.adb.org/publications/series/south-asia-working-papers"

    def __init__(self):
        super().__init__("ADB", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch ADB South Asia Working Papers."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # ADB publication cards: <a> wraps <h3> with title
            for link in soup.find_all('a', href=lambda h: h and '/publications/' in str(h) and 'series' not in str(h)):
                # Only consider links that contain a heading (these are publication cards)
                heading = link.find(['h3', 'h4'])
                if not heading:
                    continue

                title = heading.get_text(strip=True)
                href = link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue

                # Skip navigation/generic links
                skip_titles = ['read more', 'view all', 'download', 'pdf',
                               'latest publications', 'related publications']
                if title.lower().strip() in skip_titles:
                    continue

                # Use the link's parent container for metadata
                item = link.find_parent(['div', 'article', 'li']) or link

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://www.adb.org{href}"

                # Try to find date - check the link text first (contains "Category | DD Mon YYYY")
                date_text = None
                link_text = link.get_text()
                parent_text = item.get_text() if item != link else link_text

                # Match various date formats - check link text first, then parent
                date_match = re.search(
                    r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
                    link_text
                )
                if not date_match:
                    date_match = re.search(
                        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
                        parent_text
                    )
                if date_match:
                    date_text = parse_date_flexible(date_match.group(1))

                if not date_text:
                    # Try "Month YYYY" format
                    date_match = re.search(
                        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                        parent_text
                    )
                    if date_match:
                        date_text = parse_date_flexible(date_match.group(1))

                if not date_text:
                    # Try year only
                    year_match = re.search(r'\b(202[4-9])\b', parent_text)
                    if year_match:
                        date_text = f"{year_match.group(1)}-01-01"

                if date_text and not is_recent(date_text):
                    continue

                yield Paper(
                    title=title,
                    authors="ADB",
                    abstract=f"ADB South Asia Working Paper: {title}",
                    url=url,
                    source="ADB",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching ADB papers: {e}")
