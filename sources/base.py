"""Base fetcher class and India-relevance filtering."""

import re
from abc import ABC, abstractmethod
from typing import Iterator
from db import Paper


# Keywords for India-relevance detection
INDIA_KEYWORDS = [
    # Country and demonyms
    r'\bIndia\b', r'\bIndian\b', r'\bIndia\'s\b',
    r'\bSubcontinent\b', r'\bSouth Asia\b', r'\bSouth Asian\b',

    # Institutions
    r'\bRBI\b', r'\bReserve Bank of India\b',
    r'\bSEBI\b', r'\bSecurities and Exchange Board\b',
    r'\bNSE\b', r'\bBSE\b', r'\bNational Stock Exchange\b', r'\bBombay Stock Exchange\b',
    r'\bNIPFP\b', r'\bNCAER\b', r'\bNBER.*India\b',
    r'\bIIM\b', r'\bIIT\b', r'\bISB\b', r'\bISI Kolkata\b', r'\bISI Delhi\b',
    r'\bJNU\b', r'\bDSE\b', r'\bIGIDR\b', r'\bCPR\b', r'\bCSDS\b',

    # Currency and markets
    r'\brupee\b', r'\brupees\b', r'\bINR\b',
    r'\bNifty\b', r'\bSensex\b',

    # Cities and states (comprehensive)
    r'\bMumbai\b', r'\bDelhi\b', r'\bNew Delhi\b', r'\bBangalore\b', r'\bBengaluru\b',
    r'\bChennai\b', r'\bHyderabad\b', r'\bKolkata\b', r'\bPune\b', r'\bAhmedabad\b',
    r'\bJaipur\b', r'\bLucknow\b', r'\bKanpur\b', r'\bNagpur\b', r'\bSurat\b',
    r'\bMaharashtra\b', r'\bKarnataka\b', r'\bTamil Nadu\b', r'\bGujarat\b',
    r'\bUttar Pradesh\b', r'\bWest Bengal\b', r'\bRajasthan\b', r'\bKerala\b',
    r'\bAndhra Pradesh\b', r'\bTelangana\b', r'\bBihar\b', r'\bMadhya Pradesh\b',
    r'\bOdisha\b', r'\bPunjab\b', r'\bHaryana\b', r'\bAssam\b', r'\bJharkhand\b',
    r'\bChhattisgarh\b', r'\bUttarakhand\b', r'\bGoa\b', r'\bHimachal\b',

    # Major companies
    r'\bTata\b', r'\bReliance\b', r'\bInfosys\b', r'\bWipro\b', r'\bTCS\b',
    r'\bHDFC\b', r'\bICICI\b', r'\bSBI\b', r'\bBharti\b', r'\bAirtel\b',
    r'\bMahindra\b', r'\bBajaj\b', r'\bAdani\b', r'\bHindustan\b',
    r'\bLarsen\b', r'\bL&T\b', r'\bMaruti\b', r'\bHero\b', r'\bBirla\b',
    r'\bVedanta\b', r'\bJindal\b', r'\bGodrej\b', r'\bITC\b',

    # Programs and policies
    r'\bMahatma Gandhi\b', r'\bMGNREGA\b', r'\bAadhaar\b', r'\bUPI\b',
    r'\bJan Dhan\b', r'\bMake in India\b', r'\bGST\b', r'\bDemonetization\b',
    r'\bDigital India\b', r'\bSwachh Bharat\b', r'\bPMJDY\b', r'\bPM-KISAN\b',
    r'\bStartup India\b', r'\bSkill India\b', r'\bAyushman Bharat\b',
]

# Compile patterns for efficiency
INDIA_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in INDIA_KEYWORDS]


def is_india_relevant(title: str, abstract: str = "", authors: str = "") -> bool:
    """
    Check if a paper is India-relevant based on title, abstract, and authors.
    Returns True if any India-related keyword is found.
    """
    text = f"{title} {abstract} {authors}"

    for pattern in INDIA_PATTERNS:
        if pattern.search(text):
            return True

    return False


# Sources that are inherently India-focused
INDIA_SOURCES = {
    'RBI', 'SEBI', 'NIPFP', 'NCAER', 'EPW', 'XKDR',
    'Vikalpa', 'IIMB Management Review', 'Decision', 'IIMK Management Review'
}


def is_india_source(source: str) -> bool:
    """Check if a source is inherently India-focused."""
    return source in INDIA_SOURCES


class BaseFetcher(ABC):
    """Base class for all paper fetchers."""

    def __init__(self, source_name: str, category: str):
        self.source_name = source_name
        self.category = category

    @abstractmethod
    def fetch(self) -> Iterator[Paper]:
        """Fetch papers from the source. Yields Paper objects."""
        pass

    def should_include(self, paper: Paper) -> bool:
        """
        Determine if a paper should be included.
        India sources include all papers; others need India relevance.
        """
        if is_india_source(self.source_name):
            paper.is_india_specific = True
            return True

        # For non-India sources, check relevance
        if is_india_relevant(paper.title, paper.abstract, paper.authors):
            paper.is_india_specific = True
            return True

        # Could add logic for globally important papers here
        return False
