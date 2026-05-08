"""Indian institution scrapers: RBI, SEBI, NIPFP, NCAER."""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Iterator, Optional
from db import Paper
from .base import BaseFetcher


# Only include papers from 2024 onwards
CUTOFF_DATE = datetime(2024, 1, 1)


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None

    formats = [
        "%b %d, %Y",  # Dec 31, 2024
        "%B %d, %Y",  # December 31, 2024
        "%Y-%m-%d",   # 2024-12-31
        "%d/%m/%Y",   # 31/12/2024
        "%d-%m-%Y",   # 31-12-2024
    ]

    date_str = date_str.strip()
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def is_recent(date_str: str) -> bool:
    """Check if date is within last 3 years."""
    if not date_str:
        return True  # Include if no date (will be filtered later)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt >= CUTOFF_DATE
    except:
        return True


class RBIFetcher(BaseFetcher):
    """Fetcher for RBI working papers."""

    WORKING_PAPERS_URL = "https://www.rbi.org.in/Scripts/OccasionalPublications.aspx?head=Working%20Papers"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    def __init__(self):
        super().__init__("RBI", "policy")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from RBI website."""
        try:
            response = requests.get(self.WORKING_PAPERS_URL, headers=self.HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            current_date = None

            # Find the main table with papers
            for row in soup.find_all('tr'):
                # Check for date header
                date_header = row.find('td', class_='tableheader')
                if date_header:
                    date_text = date_header.get_text(strip=True)
                    current_date = parse_date(date_text)
                    continue

                # Look for paper links
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # First cell: title link
                    title_link = cells[0].find('a', class_='link2')
                    if not title_link:
                        continue

                    title = title_link.get_text(strip=True)
                    if not title or len(title) < 20:
                        continue

                    # Second cell: authors
                    authors = cells[1].get_text(strip=True) if len(cells) > 1 else "RBI"

                    # Find PDF link
                    pdf_link = row.find('a', href=lambda h: h and '.PDF' in h.upper())
                    if pdf_link:
                        url = pdf_link.get('href', '')
                    else:
                        # Use the publication view link
                        href = title_link.get('href', '')
                        url = f"https://www.rbi.org.in/Scripts/{href}" if href else ""

                    if not url:
                        continue

                    # Check if recent
                    if current_date and not is_recent(current_date):
                        continue

                    yield Paper(
                        title=title,
                        authors=authors,
                        abstract=f"RBI Working Paper: {title}",
                        url=url,
                        source="RBI",
                        category="policy",
                        published_date=current_date,
                        is_india_specific=True
                    )

        except Exception as e:
            print(f"  Error fetching RBI papers: {e}")


class SEBIFetcher(BaseFetcher):
    """Fetcher for SEBI working papers and research."""

    # SEBI working papers and research papers pages
    PAPERS_URLS = [
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=4&ssid=81&smid=104",  # Working Papers
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=4&ssid=81&smid=109",  # Research Papers
    ]

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    def __init__(self):
        super().__init__("SEBI", "finance")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from SEBI website."""
        seen_urls = set()

        for papers_url in self.PAPERS_URLS:
            try:
                response = requests.get(papers_url, headers=self.HEADERS, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'lxml')

                # Find paper entries in table rows or list items
                for row in soup.find_all(['tr', 'li', 'div']):
                    # Look for links with PDF or detail pages
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)

                        # Skip navigation and generic links
                        if not text or len(text) < 15:
                            continue
                        if href in seen_urls:
                            continue

                        # Look for paper links (PDF, working papers, or detail pages)
                        is_paper = (
                            '.pdf' in href.lower() or
                            '/legal/' in href.lower() or
                            '/reports/working-papers/' in href.lower() or
                            '/reports/research/' in href.lower() or
                            'doGet' in href
                        )

                        if is_paper:
                            url = href if href.startswith('http') else f"https://www.sebi.gov.in{href}"
                            seen_urls.add(href)

                            # Try to extract date from nearby elements
                            date_text = None
                            for sibling in row.find_all(['td', 'span']):
                                sib_text = sibling.get_text(strip=True)
                                parsed = parse_date(sib_text)
                                if parsed:
                                    date_text = parsed
                                    break

                            # Only include recent papers
                            if date_text and not is_recent(date_text):
                                continue

                            yield Paper(
                                title=text,
                                authors="SEBI",
                                abstract=f"SEBI Research: {text}",
                                url=url,
                                source="SEBI",
                                category="finance",
                                published_date=date_text,
                                is_india_specific=True
                            )

            except Exception as e:
                print(f"  Error fetching SEBI papers from {papers_url}: {e}")


class NIPFPFetcher(BaseFetcher):
    """Fetcher for NIPFP working papers."""

    PAPERS_URL = "https://www.nipfp.org.in/publication-index-page/working-paper-index-page/"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    def __init__(self):
        super().__init__("NIPFP", "policy")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from NIPFP website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=self.HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_titles = set()

            # Find paper titles in h3 tags
            for h3 in soup.find_all('h3'):
                title = h3.get_text(strip=True)
                if not title or len(title) < 20 or title in seen_titles:
                    continue

                seen_titles.add(title)

                # Find the corresponding "Comment" link which has the paper URL
                parent = h3.parent
                link = None

                # Search in parent and siblings for the link
                for container in [parent, parent.parent if parent else None]:
                    if container:
                        link = container.find('a', href=lambda h: h and '/working-paper-index-page/' in h and not h.endswith('working-paper-index-page/'))
                        if link:
                            break

                if link:
                    href = link.get('href', '')
                    url = f"https://www.nipfp.org.in{href}" if href.startswith('/') else href

                    yield Paper(
                        title=title,
                        authors="NIPFP",
                        abstract=f"NIPFP Working Paper: {title}",
                        url=url,
                        source="NIPFP",
                        category="policy",
                        is_india_specific=True
                    )

        except Exception as e:
            print(f"  Error fetching NIPFP papers: {e}")


class NCAERFetcher(BaseFetcher):
    """Fetcher for NCAER reports (books/reports, working papers, flagship publications)."""

    API_URL = "https://ncaer.org/wp-json/wp/v2/publication"

    # publication-category-<slug> values to keep. Excludes op-eds, blogs,
    # newsletters, journal articles, and other non-report content.
    REPORT_CATEGORIES = {
        'books-reports',
        'working-papers',
        'flagship-publication',
    }

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    def __init__(self):
        super().__init__("NCAER", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch reports from NCAER WP REST API."""
        seen_urls = set()
        for page in range(1, 6):  # up to ~500 newest publications
            try:
                response = requests.get(
                    self.API_URL,
                    params={'per_page': 100, 'page': page, '_embed': 0},
                    headers=self.HEADERS,
                    timeout=30,
                )
                if response.status_code == 400:
                    break  # past last page
                response.raise_for_status()
                items = response.json()
            except Exception as e:
                print(f"  Error fetching NCAER page {page}: {e}")
                return

            if not items:
                break

            for item in items:
                cats = {
                    c.replace('publication-category-', '')
                    for c in item.get('class_list', [])
                    if c.startswith('publication-category-')
                }
                if not cats & self.REPORT_CATEGORIES:
                    continue

                url = item.get('link', '')
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = BeautifulSoup(
                    item.get('title', {}).get('rendered', ''), 'lxml'
                ).get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                excerpt_html = item.get('excerpt', {}).get('rendered', '')
                excerpt = BeautifulSoup(excerpt_html, 'lxml').get_text(' ', strip=True)
                kind = next(iter(cats & self.REPORT_CATEGORIES))
                kind_label = kind.replace('-', ' ').title()
                abstract = excerpt or f"NCAER {kind_label}: {title}"

                date_str = (item.get('date') or '')[:10] or None

                yield Paper(
                    title=title,
                    authors="NCAER",
                    abstract=abstract,
                    url=url,
                    source="NCAER",
                    category="economics",
                    published_date=date_str,
                    is_india_specific=True,
                )
