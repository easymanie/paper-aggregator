"""Scraper for Kiel Institute for the World Economy working papers."""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Iterator
from db import Paper
from .base import BaseFetcher, is_india_relevant


class KielFetcher(BaseFetcher):
    """Fetcher for Kiel Institute working papers."""

    # Search all publications for India-related content
    SEARCH_URL = "https://www.kielinstitut.de/publications/"

    def __init__(self):
        super().__init__("Kiel Institute", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch India-relevant working papers from Kiel Institute."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # Search for India-related publications
            seen_urls = set()
            url = f"{self.SEARCH_URL}?q=India"

            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find publication teasers
            for teaser in soup.select('article.publication-page-teaser'):
                paper = self._parse_teaser(teaser)
                if paper and paper.url not in seen_urls:
                    seen_urls.add(paper.url)
                    if self.should_include(paper):
                        yield paper

        except Exception as e:
            print(f"Error fetching Kiel papers: {e}")

    def _parse_teaser(self, teaser) -> Paper | None:
        """Parse a publication teaser into a Paper object."""
        try:
            # Get title and link
            title_elem = teaser.select_one('.publication-page-teaser__headline a')
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if not title:
                return None

            url = title_elem.get('href', '')
            if url and not url.startswith('http'):
                url = f"https://www.kielinstitut.de{url}"

            # Get authors
            author_elem = teaser.select_one('.publication-page-teaser__author')
            authors = author_elem.get_text(strip=True) if author_elem else ''

            # Get publication date
            date_elem = teaser.select_one('.published-date')
            published_date = None
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Parse dates like "12/2025" or "forthcoming"
                date_match = re.search(r'(\d{1,2})/(\d{4})', date_text)
                if date_match:
                    month, year = date_match.groups()
                    published_date = f"{year}-{int(month):02d}-01"

            # Get category/type
            category_elem = teaser.select_one('.meta__category')
            paper_type = category_elem.get_text(strip=True) if category_elem else ''

            return Paper(
                title=title,
                authors=authors,
                abstract='',  # Abstract not on listing page
                url=url,
                source=self.source_name,
                category=self.category,
                published_date=published_date,
                is_india_specific=False
            )

        except Exception as e:
            return None

    def should_include(self, paper: Paper) -> bool:
        """Check if paper is India-relevant."""
        return is_india_relevant(paper.title, paper.abstract, paper.authors)
