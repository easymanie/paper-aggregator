"""UNCTAD publications fetcher (India-filtered)."""

import re
import requests
from bs4 import BeautifulSoup
from typing import Iterator
from db import Paper
from .base import BaseFetcher


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


class UNCTADFetcher(BaseFetcher):
    """Fetcher for UNCTAD publications (India-filtered)."""

    PAPERS_URL = "https://unctad.org/publications"

    def __init__(self):
        super().__init__("UNCTAD", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch publications from UNCTAD, filtering for India relevance."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find publication links
            for link in soup.find_all('a', href=lambda h: h and '/publication/' in h):
                href = link.get('href', '')

                # Skip anchors and duplicate URLs
                if '#' in href or href in seen_urls:
                    continue

                title = link.get_text(strip=True)
                if not title or len(title) < 15:
                    continue

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://unctad.org{href}"

                # Try to find date from parent element
                date_text = None
                parent = link.find_parent(['div', 'article', 'li'])
                if parent:
                    parent_text = parent.get_text()
                    # Match "DD Mon YYYY" format
                    date_match = re.search(
                        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
                        parent_text
                    )
                    if date_match:
                        from .thinktanks import parse_date_flexible
                        date_text = parse_date_flexible(date_match.group(1))

                paper = Paper(
                    title=title,
                    authors="UNCTAD",
                    abstract=f"UNCTAD Publication: {title}",
                    url=url,
                    source="UNCTAD",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=False
                )

                if self.should_include(paper):
                    yield paper

        except Exception as e:
            print(f"  Error fetching UNCTAD publications: {e}")
