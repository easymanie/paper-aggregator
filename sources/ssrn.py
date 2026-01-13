"""SSRN paper fetcher using RSS feeds."""

import feedparser
from datetime import datetime
from typing import Iterator, Optional
from db import Paper
from .base import BaseFetcher, is_india_relevant


class SSRNFetcher(BaseFetcher):
    """
    Fetcher for SSRN papers related to India.

    SSRN blocks direct scraping, so we use their RSS feeds for specific
    research networks/journals that are likely to have India-related content.
    """

    # SSRN RSS feeds for economics/finance research networks
    # These are public RSS feeds that don't require authentication
    RSS_FEEDS = [
        # Development Economics
        ("https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=1002844&Network=no&lim=false&npage=1&rss=yes", "economics", "SSRN Development Economics"),
        # Financial Economics
        ("https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=1002772&Network=no&lim=false&npage=1&rss=yes", "finance", "SSRN Financial Economics"),
        # Public Economics
        ("https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=1002807&Network=no&lim=false&npage=1&rss=yes", "economics", "SSRN Public Economics"),
        # International Trade
        ("https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=1002791&Network=no&lim=false&npage=1&rss=yes", "economics", "SSRN International Trade"),
        # Corporate Governance
        ("https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=916745&Network=no&lim=false&npage=1&rss=yes", "management", "SSRN Corporate Governance"),
        # Banking & Insurance
        ("https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=1002769&Network=no&lim=false&npage=1&rss=yes", "finance", "SSRN Banking"),
    ]

    def __init__(self):
        super().__init__("SSRN", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch India-related papers from SSRN RSS feeds."""
        seen_urls = set()

        for feed_url, category, feed_name in self.RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)

                if feed.bozo and not feed.entries:
                    continue

                for entry in feed.entries:
                    paper = self._parse_entry(entry, category)
                    if paper and paper.url not in seen_urls:
                        # Only include India-relevant papers
                        if is_india_relevant(paper.title, paper.abstract, paper.authors):
                            paper.is_india_specific = True
                            seen_urls.add(paper.url)
                            yield paper

            except Exception as e:
                # Silently continue on feed errors
                continue

    def _parse_entry(self, entry, category: str) -> Optional[Paper]:
        """Parse an RSS feed entry."""
        try:
            title = entry.get('title', '').strip()
            if not title:
                return None

            url = entry.get('link', '')
            if not url:
                return None

            # Get abstract
            abstract = entry.get('summary', '') or entry.get('description', '')
            if abstract:
                import re
                import html
                abstract = re.sub(r'<[^>]+>', '', abstract)
                abstract = html.unescape(abstract)
                abstract = ' '.join(abstract.split())

            # Get authors
            authors = ''
            if 'authors' in entry:
                authors = ', '.join(a.get('name', '') for a in entry.authors if a.get('name'))
            elif 'author' in entry:
                authors = entry.author

            # Get date
            published_date = None
            for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                if date_field in entry and entry[date_field]:
                    try:
                        published_date = datetime(*entry[date_field][:3]).strftime("%Y-%m-%d")
                        break
                    except:
                        pass

            return Paper(
                title=title,
                authors=authors,
                abstract=abstract[:5000] if abstract else "",
                url=url,
                source="SSRN",
                category=category,
                published_date=published_date,
                is_india_specific=False
            )

        except Exception:
            return None
