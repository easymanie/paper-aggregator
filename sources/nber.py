"""NBER working papers fetcher."""

import feedparser
from datetime import datetime
from typing import Iterator, Optional
from db import Paper
from .base import BaseFetcher


class NBERFetcher(BaseFetcher):
    """Fetcher for NBER working papers."""

    FEED_URL = "https://www.nber.org/rss/new.xml"

    def __init__(self):
        super().__init__("NBER", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from NBER RSS feed, filtering for India relevance."""
        try:
            feed = feedparser.parse(self.FEED_URL)

            if feed.bozo and not feed.entries:
                print(f"  Warning: Could not parse NBER feed")
                return

            for entry in feed.entries:
                paper = self._parse_entry(entry)
                if paper and self.should_include(paper):
                    yield paper

        except Exception as e:
            print(f"  Error fetching NBER: {e}")

    def _parse_entry(self, entry) -> Optional[Paper]:
        """Parse a feed entry into a Paper object."""
        try:
            title = entry.get('title', '').strip()
            if not title:
                return None

            url = entry.get('link', '')
            if not url:
                return None

            # Get abstract
            abstract = entry.get('summary', '')
            if abstract:
                import re
                import html
                abstract = re.sub(r'<[^>]+>', '', abstract)
                abstract = html.unescape(abstract)
                abstract = ' '.join(abstract.split())

            # Get authors
            authors = ''
            if 'authors' in entry:
                authors = ', '.join(a.get('name', '') for a in entry.authors)
            elif 'author' in entry:
                authors = entry.author

            # Get published date
            published_date = None
            if 'published_parsed' in entry and entry.published_parsed:
                try:
                    published_date = datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
                except:
                    pass

            return Paper(
                title=title,
                authors=authors,
                abstract=abstract[:5000],
                url=url,
                source="NBER",
                category="economics",
                published_date=published_date,
                is_india_specific=False
            )

        except Exception as e:
            print(f"  Error parsing NBER entry: {e}")
            return None
