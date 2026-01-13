"""RSS-based fetcher for academic journals."""

import feedparser
from datetime import datetime, timedelta
from typing import Iterator, Optional
from db import Paper
from .base import BaseFetcher, is_india_relevant


# Only include papers from last 3 years
CUTOFF_DATE = datetime.now() - timedelta(days=3*365)


class JournalFetcher(BaseFetcher):
    """Fetcher for journals with RSS feeds."""

    def __init__(
        self,
        source_name: str,
        feed_url: str,
        category: str,
        india_only: bool = True
    ):
        super().__init__(source_name, category)
        self.feed_url = feed_url
        self.india_only = india_only

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from the RSS feed."""
        try:
            feed = feedparser.parse(self.feed_url)

            if feed.bozo and not feed.entries:
                print(f"  Warning: Could not parse feed for {self.source_name}")
                return

            for entry in feed.entries:
                paper = self._parse_entry(entry)
                if paper:
                    # Check if paper is recent (last 3 years)
                    if paper.published_date:
                        try:
                            pub_date = datetime.strptime(paper.published_date, "%Y-%m-%d")
                            if pub_date < CUTOFF_DATE:
                                continue
                        except:
                            pass

                    if not self.india_only or self.should_include(paper):
                        yield paper

        except Exception as e:
            print(f"  Error fetching {self.source_name}: {e}")

    def _parse_entry(self, entry) -> Optional[Paper]:
        """Parse a feed entry into a Paper object."""
        try:
            title = entry.get('title', '').strip()
            if not title:
                return None

            # Get URL
            url = entry.get('link', '')
            if not url:
                return None

            # Get abstract/description
            abstract = ''
            if 'summary' in entry:
                abstract = entry.summary
            elif 'description' in entry:
                abstract = entry.description

            # Clean HTML from abstract
            abstract = self._clean_html(abstract)

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
            elif 'updated_parsed' in entry and entry.updated_parsed:
                try:
                    published_date = datetime(*entry.updated_parsed[:3]).strftime("%Y-%m-%d")
                except:
                    pass

            return Paper(
                title=title,
                authors=authors,
                abstract=abstract[:5000],  # Limit abstract length
                url=url,
                source=self.source_name,
                category=self.category,
                published_date=published_date,
                is_india_specific=False  # Will be set by should_include
            )

        except Exception as e:
            print(f"  Error parsing entry: {e}")
            return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        import html
        clean = html.unescape(clean)
        # Normalize whitespace
        clean = ' '.join(clean.split())
        return clean.strip()
