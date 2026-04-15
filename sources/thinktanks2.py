"""Fetchers for additional Indian think tanks."""

import re
import requests
from bs4 import BeautifulSoup
from typing import Iterator
from db import Paper
from .base import BaseFetcher
from .thinktanks import HEADERS, parse_date_flexible, is_recent


class ORFFetcher(BaseFetcher):
    """Fetcher for Observer Research Foundation research articles."""

    # ORF organizes by content type, not a single /research listing
    CONTENT_URLS = [
        "https://www.orfonline.org/content-type/occasional-paper",
        "https://www.orfonline.org/expert-speak",
    ]

    def __init__(self):
        super().__init__("ORF", "policy")

    def fetch(self) -> Iterator[Paper]:
        """Fetch research articles from ORF website."""
        seen_urls = set()

        for page_url in self.CONTENT_URLS:
            try:
                response = requests.get(page_url, headers=HEADERS, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'lxml')

                # ORF lists research articles as cards with links to /research/
                for item in soup.find_all(['article', 'div', 'li']):
                    link = item.find('a', href=lambda h: h and '/research/' in str(h))
                    if not link:
                        continue

                    href = link.get('href', '')
                    if href in seen_urls:
                        continue

                    title = link.get_text(strip=True)

                    if not title or len(title) < 15:
                        heading = item.find(['h2', 'h3', 'h4'])
                        if heading:
                            title = heading.get_text(strip=True)

                    if not title or len(title) < 15:
                        continue

                    skip_words = ['read more', 'view all', 'see all', 'load more']
                    if title.lower().strip() in skip_words:
                        continue

                    seen_urls.add(href)
                    url = href if href.startswith('http') else f"https://www.orfonline.org{href}"

                    # Try to find date
                    date_text = None
                    date_elem = item.find(['time', 'span'], class_=lambda x: x and 'date' in str(x).lower())
                    if date_elem:
                        date_text = parse_date_flexible(date_elem.get_text(strip=True))

                    if not date_text:
                        time_elem = item.find('time')
                        if time_elem and time_elem.get('datetime'):
                            dt_str = time_elem.get('datetime', '')[:10]
                            if re.match(r'\d{4}-\d{2}-\d{2}', dt_str):
                                date_text = dt_str

                    if not date_text:
                        parent_text = item.get_text()
                        date_match = re.search(
                            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
                            parent_text
                        )
                        if date_match:
                            date_text = parse_date_flexible(date_match.group(1))

                    if date_text and not is_recent(date_text):
                        continue

                    authors = "ORF"
                    author_elem = item.find(['span', 'p', 'div'], class_=lambda x: x and 'author' in str(x).lower())
                    if author_elem:
                        authors = author_elem.get_text(strip=True) or "ORF"

                    yield Paper(
                        title=title,
                        authors=authors,
                        abstract=f"ORF Research: {title}",
                        url=url,
                        source="ORF",
                        category="policy",
                        published_date=date_text,
                        is_india_specific=True
                    )

            except Exception as e:
                print(f"  Error fetching ORF from {page_url}: {e}")


class CarnegieIndiaFetcher(BaseFetcher):
    """Fetcher for Carnegie Endowment India program research."""

    PAPERS_URL = "https://carnegieendowment.org/india"

    def __init__(self):
        super().__init__("Carnegie India", "policy")

    def fetch(self) -> Iterator[Paper]:
        """Fetch research from Carnegie India."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Carnegie lists articles/publications as cards
            for item in soup.find_all(['article', 'div', 'li']):
                link = item.find('a', href=lambda h: h and (
                    '/research/' in str(h) or '/posts/' in str(h) or
                    '/publications/' in str(h)
                ))
                if not link:
                    continue

                href = link.get('href', '')
                if href in seen_urls:
                    continue

                title = link.get_text(strip=True)

                if not title or len(title) < 15:
                    heading = item.find(['h2', 'h3', 'h4'])
                    if heading:
                        title = heading.get_text(strip=True)

                if not title or len(title) < 15:
                    continue

                skip_words = ['read more', 'view all', 'see all', 'load more']
                if title.lower().strip() in skip_words:
                    continue

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://carnegieendowment.org{href}"

                # Try to find date
                date_text = None
                time_elem = item.find('time')
                if time_elem:
                    if time_elem.get('datetime'):
                        dt_str = time_elem.get('datetime', '')[:10]
                        if re.match(r'\d{4}-\d{2}-\d{2}', dt_str):
                            date_text = dt_str
                    if not date_text:
                        date_text = parse_date_flexible(time_elem.get_text(strip=True))

                if not date_text:
                    parent_text = item.get_text()
                    date_match = re.search(
                        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
                        parent_text
                    )
                    if date_match:
                        date_text = parse_date_flexible(date_match.group(1))

                if date_text and not is_recent(date_text):
                    continue

                authors = "Carnegie India"
                author_elem = item.find(['span', 'p', 'div'], class_=lambda x: x and 'author' in str(x).lower())
                if author_elem:
                    authors = author_elem.get_text(strip=True) or "Carnegie India"

                yield Paper(
                    title=title,
                    authors=authors,
                    abstract=f"Carnegie India: {title}",
                    url=url,
                    source="Carnegie India",
                    category="policy",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching Carnegie India papers: {e}")


class EPWFetcher(BaseFetcher):
    """Fetcher for Economic and Political Weekly articles."""

    PAPERS_URL = "https://www.epw.in"

    def __init__(self):
        super().__init__("EPW", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch recent articles from EPW website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # EPW homepage and article listing pages
            for item in soup.find_all(['article', 'div', 'li']):
                link = item.find('a', href=lambda h: h and (
                    '/journal/' in str(h) or '/article/' in str(h)
                ))
                if not link:
                    continue

                href = link.get('href', '')
                if href in seen_urls:
                    continue

                title = link.get_text(strip=True)

                if not title or len(title) < 15:
                    heading = item.find(['h2', 'h3', 'h4'])
                    if heading:
                        title = heading.get_text(strip=True)

                if not title or len(title) < 15:
                    continue

                skip_words = ['read more', 'view all', 'current issue', 'subscribe',
                              'back issues', 'archive', 'about']
                if title.lower().strip() in skip_words:
                    continue
                if re.match(r'^vol\.\s*\d+,\s*issue no\.', title, re.IGNORECASE):
                    continue

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://www.epw.in{href}"

                # Try to find date
                date_text = None
                date_elem = item.find(['time', 'span'], class_=lambda x: x and 'date' in str(x).lower())
                if date_elem:
                    date_text = parse_date_flexible(date_elem.get_text(strip=True))

                if not date_text:
                    time_elem = item.find('time')
                    if time_elem and time_elem.get('datetime'):
                        dt_str = time_elem.get('datetime', '')[:10]
                        if re.match(r'\d{4}-\d{2}-\d{2}', dt_str):
                            date_text = dt_str

                if not date_text:
                    parent_text = item.get_text()
                    date_match = re.search(
                        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
                        parent_text
                    )
                    if date_match:
                        date_text = parse_date_flexible(date_match.group(1))

                if date_text and not is_recent(date_text):
                    continue

                authors = "EPW"
                author_elem = item.find(['span', 'p', 'div'], class_=lambda x: x and 'author' in str(x).lower())
                if author_elem:
                    authors = author_elem.get_text(strip=True) or "EPW"

                yield Paper(
                    title=title,
                    authors=authors,
                    abstract=f"Economic and Political Weekly: {title}",
                    url=url,
                    source="EPW",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching EPW articles: {e}")
