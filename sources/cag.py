"""CAG (Comptroller and Auditor General of India) audit reports fetcher."""

import re
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from typing import Iterator
from db import Paper
from .base import BaseFetcher
from .thinktanks import parse_date_flexible, is_recent

# Suppress InsecureRequestWarning for CAG's SSL cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

MAX_PAGES = 3  # Fetch first 3 pages (~30 reports)


class CAGFetcher(BaseFetcher):
    """Fetcher for CAG audit reports."""

    BASE_URL = "https://cag.gov.in/en/audit-report"

    def __init__(self):
        super().__init__("CAG", "policy")

    def _get_with_retry(self, session, url, retries=3):
        """GET with retry for flaky CAG server."""
        for attempt in range(retries):
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except (requests.ConnectionError, requests.Timeout):
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    raise

    def fetch(self) -> Iterator[Paper]:
        """Fetch audit reports from CAG website."""
        session = requests.Session()
        session.headers.update(HEADERS)
        session.verify = False

        for page in range(1, MAX_PAGES + 1):
            try:
                url = self.BASE_URL if page == 1 else f"{self.BASE_URL}?page={page}"
                response = self._get_with_retry(session, url)

                soup = BeautifulSoup(response.content, 'lxml')
                count = 0

                for listing in soup.find_all('div', class_='AuditReportlisting'):
                    paper = self._parse_listing(listing)
                    if paper:
                        count += 1
                        yield paper

                # Stop if no results on this page
                if count == 0:
                    break

            except Exception as e:
                print(f"  Error fetching CAG page {page}: {e}")
                break

    def _parse_listing(self, listing) -> Paper | None:
        """Parse a single audit report listing."""
        # Title and detail URL
        detail_div = listing.find('div', class_='reportDetail')
        if not detail_div:
            return None

        title_link = detail_div.find('a', href=True)
        if not title_link:
            return None

        title = title_link.get_text(strip=True)
        if not title or len(title) < 10:
            return None

        href = title_link.get('href', '')
        detail_url = href if href.startswith('http') else f"https://cag.gov.in{href}"

        # Date
        date_text = None
        date_elem = listing.find('span', class_='dtn')
        if date_elem:
            date_text = parse_date_flexible(date_elem.get_text(strip=True))

        if date_text and not is_recent(date_text):
            return None

        # Report type
        report_type = ""
        type_elem = listing.find('div', class_='reportType')
        if type_elem:
            span = type_elem.find('span')
            if span:
                report_type = span.get_text(strip=True)

        # State/department
        state = ""
        icon_div = listing.find('div', class_='reportIcon')
        if icon_div:
            h5 = icon_div.find('h5')
            if h5:
                state = h5.get_text(strip=True)

        # Sector
        sector = ""
        sector_div = listing.find('div', class_='sectorDetail')
        if sector_div:
            divs = sector_div.find_all('div')
            if len(divs) >= 2:
                sector = divs[1].get_text(strip=True)

        # PDF URL
        pdf_url = None
        pdf_div = listing.find('div', class_='pdfcallBlock')
        if pdf_div:
            pdf_link = pdf_div.find('a', href=lambda h: h and '.pdf' in h.lower())
            if pdf_link:
                pdf_href = pdf_link.get('href', '')
                pdf_url = pdf_href if pdf_href.startswith('http') else f"https://cag.gov.in{pdf_href}"

        # Build abstract with metadata
        parts = []
        if report_type:
            parts.append(f"Type: {report_type}")
        if state:
            parts.append(f"Entity: {state}")
        if sector:
            parts.append(f"Sector: {sector}")
        abstract = f"CAG Audit Report. {'. '.join(parts)}." if parts else f"CAG Audit Report: {title}"

        # Use PDF URL if available, otherwise detail page
        url = pdf_url or detail_url

        return Paper(
            title=title,
            authors="CAG",
            abstract=abstract,
            url=url,
            source="CAG",
            category="policy",
            published_date=date_text,
            is_india_specific=True
        )
