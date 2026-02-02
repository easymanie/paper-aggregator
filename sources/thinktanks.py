"""Fetchers for Indian think tanks and educational institutions."""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Iterator, Optional
from db import Paper
from .base import BaseFetcher


CUTOFF_DATE = datetime(2024, 1, 1)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def parse_date_flexible(date_str: str) -> Optional[str]:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None

    date_str = date_str.strip()

    formats = [
        "%b %d, %Y",      # Dec 31, 2024
        "%B %d, %Y",      # December 31, 2024
        "%B %Y",          # December 2024
        "%b %Y",          # Dec 2024
        "%Y-%m-%d",       # 2024-12-31
        "%d/%m/%Y",       # 31/12/2024
        "%d-%m-%Y",       # 31-12-2024
        "%d %b %Y",       # 31 Dec 2024
        "%d %B %Y",       # 31 December 2024
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def is_recent(date_str: str) -> bool:
    """Check if date is from 2024 onwards."""
    if not date_str:
        return True
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt >= CUTOFF_DATE
    except:
        return True


class ICRIERFetcher(BaseFetcher):
    """Fetcher for ICRIER working papers."""

    PAPERS_URL = "https://icrier.org/publications_category/working-papers/"

    def __init__(self):
        super().__init__("ICRIER", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from ICRIER website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find all publication links
            for link in soup.find_all('a', href=lambda h: h and '/publications/' in h):
                title = link.get_text(strip=True)
                href = link.get('href', '')

                # Skip category/navigation links
                if 'category' in href or 'categorie' in href:
                    continue
                if not title or len(title) < 15 or href in seen_urls:
                    continue

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://icrier.org{href}"

                yield Paper(
                    title=title,
                    authors="ICRIER",
                    abstract=f"ICRIER Working Paper: {title}",
                    url=url,
                    source="ICRIER",
                    category="economics",
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching ICRIER papers: {e}")


class CPRFetcher(BaseFetcher):
    """Fetcher for Centre for Policy Research working papers."""

    PAPERS_URL = "https://cprindia.org/working-papers/"

    def __init__(self):
        super().__init__("CPR", "policy")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from CPR website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find paper links
            for link in soup.find_all('a', href=lambda h: h and '/workingpapers/' in h):
                title = link.get_text(strip=True)
                href = link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://cprindia.org{href}"

                # Try to find author in parent/sibling
                authors = "CPR"
                parent = link.find_parent(['div', 'article', 'li'])
                if parent:
                    author_elem = parent.find(['span', 'p'], class_=lambda x: x and 'author' in str(x).lower())
                    if author_elem:
                        authors = author_elem.get_text(strip=True) or "CPR"

                yield Paper(
                    title=title,
                    authors=authors,
                    abstract=f"CPR Working Paper: {title}",
                    url=url,
                    source="CPR",
                    category="policy",
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching CPR papers: {e}")


class AshokaFetcher(BaseFetcher):
    """Fetcher for Ashoka University CEDA research papers."""

    PAPERS_URL = "https://ceda.ashoka.edu.in/researchers-corner/"

    def __init__(self):
        super().__init__("Ashoka CEDA", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from Ashoka CEDA website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find paper entries
            for article in soup.find_all(['article', 'div', 'li']):
                # Find title link pointing to ceda.ashoka.edu.in
                title_link = article.find('a', href=lambda h: h and 'ceda.ashoka.edu.in' in str(h) and h != self.PAPERS_URL)
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                href = title_link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue
                if 'researchers-corner' in href and href.rstrip('/') == self.PAPERS_URL.rstrip('/'):
                    continue

                seen_urls.add(href)
                url = href if href.startswith('http') else f"https://ceda.ashoka.edu.in{href}"

                # Try to find date
                date_text = None
                date_elem = article.find(['time', 'span'], class_=lambda x: x and 'date' in str(x).lower())
                if date_elem:
                    date_text = parse_date_flexible(date_elem.get_text(strip=True))

                yield Paper(
                    title=title,
                    authors="Ashoka CEDA",
                    abstract=f"Ashoka University CEDA: {title}",
                    url=url,
                    source="Ashoka CEDA",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching Ashoka CEDA papers: {e}")


class IIMAFetcher(BaseFetcher):
    """Fetcher for IIM Ahmedabad working papers."""

    PAPERS_URL = "https://www.iima.ac.in/faculty-research/research-publications"

    def __init__(self):
        super().__init__("IIM Ahmedabad", "management")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from IIM Ahmedabad website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find all text content that might be titles
            # The page has titles as text followed by "Read More" links
            for elem in soup.find_all(['div', 'p', 'span']):
                text = elem.get_text(strip=True)
                # Look for substantial text that could be a title
                if len(text) < 20 or len(text) > 200:
                    continue

                # Find nearby "Read More" link with /publication/
                link = elem.find_next('a', href=lambda h: h and '/publication/' in h and '/search' not in h)
                if not link:
                    continue

                href = link.get('href', '')
                if href in seen_urls:
                    continue

                # Skip if text looks like navigation or menus
                skip_phrases = ['read more', 'view all', 'home', 'faculty', 'quick links',
                                'online payment', 'verification', 'contact', 'about', 'cat ']
                if any(skip in text.lower() for skip in skip_phrases):
                    continue
                # Skip if it doesn't start with a quote or capital letter (likely a title)
                if not (text.startswith('"') or text[0].isupper()):
                    continue

                seen_urls.add(href)
                url = f"https://www.iima.ac.in{href}" if href.startswith('/') else href

                yield Paper(
                    title=text,
                    authors="IIM Ahmedabad",
                    abstract=f"IIM Ahmedabad Working Paper: {text}",
                    url=url,
                    source="IIM Ahmedabad",
                    category="management",
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching IIM Ahmedabad papers: {e}")


class IGIDRFetcher(BaseFetcher):
    """Fetcher for IGIDR working papers via IDEAS/RePEc."""

    # Use IDEAS/RePEc page for IGIDR papers
    PAPERS_URL = "https://ideas.repec.org/s/ind/igiwpp.html"

    def __init__(self):
        super().__init__("IGIDR", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from IGIDR via RePEc."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find paper entries in the list
            for li in soup.find_all('li'):
                link = li.find('a', href=lambda h: h and '/p/ind/igiwpp/' in str(h))
                if not link:
                    continue

                title = link.get_text(strip=True)
                href = link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue

                seen_urls.add(href)
                url = f"https://ideas.repec.org{href}" if href.startswith('/') else href

                # Extract year from text if available
                text = li.get_text()
                date_match = re.search(r'\b(202[4-9])\b', text)
                date_text = f"{date_match.group(1)}-01-01" if date_match else None

                # Only include recent papers
                if date_text and not is_recent(date_text):
                    continue

                # Extract authors
                authors = "IGIDR"
                author_match = re.search(r'by\s+(.+?)(?:\s*\(|\s*$)', text, re.IGNORECASE)
                if author_match:
                    authors = author_match.group(1).strip() or "IGIDR"

                yield Paper(
                    title=title,
                    authors=authors,
                    abstract=f"IGIDR Working Paper: {title}",
                    url=url,
                    source="IGIDR",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching IGIDR papers: {e}")


class ISIFetcher(BaseFetcher):
    """Fetcher for ISI Delhi discussion papers via IDEAS/RePEc."""

    PAPERS_URL = "https://ideas.repec.org/s/alo/isipdp.html"

    def __init__(self):
        super().__init__("ISI Delhi", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from ISI Delhi via RePEc."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            for li in soup.find_all('li'):
                link = li.find('a', href=lambda h: h and '/p/alo/isipdp/' in str(h))
                if not link:
                    continue

                title = link.get_text(strip=True)
                href = link.get('href', '')

                if not title or len(title) < 15 or href in seen_urls:
                    continue

                seen_urls.add(href)
                url = f"https://ideas.repec.org{href}" if href.startswith('/') else href

                text = li.get_text()
                date_match = re.search(r'\b(202[4-9])\b', text)
                date_text = f"{date_match.group(1)}-01-01" if date_match else None

                if date_text and not is_recent(date_text):
                    continue

                authors = "ISI Delhi"
                author_match = re.search(r'by\s+(.+?)(?:\s*\(|\s*$)', text, re.IGNORECASE)
                if author_match:
                    authors = author_match.group(1).strip() or "ISI Delhi"

                yield Paper(
                    title=title,
                    authors=authors,
                    abstract=f"ISI Delhi Discussion Paper: {title}",
                    url=url,
                    source="ISI Delhi",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching ISI Delhi papers: {e}")


class XKDRFetcher(BaseFetcher):
    """Fetcher for XKDR Forum working papers."""

    PAPERS_URL = "https://www.xkdr.org/papers-list"

    def __init__(self):
        super().__init__("XKDR", "economics")

    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from XKDR website."""
        try:
            response = requests.get(self.PAPERS_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            seen_urls = set()

            # Find all links to individual papers
            for link in soup.find_all('a', href=lambda h: h and '/paper/' in str(h)):
                href = link.get('href', '')

                # Skip if already seen
                if href in seen_urls:
                    continue

                # Build full URL
                url = href if href.startswith('http') else f"https://www.xkdr.org{href}"

                # Extract title - the link text or look for title element within
                title = link.get_text(strip=True)

                # Skip navigation/empty links
                if not title or len(title) < 15:
                    continue

                # Clean up title - remove paper type prefixes if they got included
                title = re.sub(r'^(Working Paper|Publication|Report|Book)\s*', '', title).strip()
                if not title or len(title) < 15:
                    continue

                seen_urls.add(href)

                # Try to find date and author info from parent/sibling elements
                date_text = None
                authors = "XKDR"

                parent = link.find_parent(['div', 'article', 'li', 'section'])
                if parent:
                    # Look for date pattern like "13 Jan 2026"
                    parent_text = parent.get_text()
                    date_match = re.search(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})', parent_text)
                    if date_match:
                        date_text = parse_date_flexible(date_match.group(1))

                    # Look for author pattern "By ..."
                    author_match = re.search(r'By\s+([^,\n]+(?:,\s*[^,\n]+)*)', parent_text)
                    if author_match:
                        authors = author_match.group(1).strip()
                        # Clean up "and X other(s)" patterns
                        authors = re.sub(r'\s+and\s+\d+\s+others?$', ' et al.', authors)

                yield Paper(
                    title=title,
                    authors=authors,
                    abstract=f"XKDR Forum: {title}",
                    url=url,
                    source="XKDR",
                    category="economics",
                    published_date=date_text,
                    is_india_specific=True
                )

        except Exception as e:
            print(f"  Error fetching XKDR papers: {e}")
