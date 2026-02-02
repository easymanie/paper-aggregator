"""Fetcher for Twitter/X accounts via OpenRSS (experimental)."""

import feedparser
import requests
from datetime import datetime
from typing import Iterator, Optional
from db import Paper
from .base import BaseFetcher, is_india_relevant

# OpenRSS provides experimental Twitter/X RSS feeds
# Note: Only captures new tweets after first subscription
OPENRSS_BASE = "https://openrss.org/feed/x.com/"

# Economics Twitter accounts to monitor
# Focus on Indian economists and global econ accounts that cover India
ECON_ACCOUNTS = [
    # Indian economists
    "kaushikcbasu",      # Kaushik Basu - former World Bank Chief Economist
    "bibekdebroy",       # Bibek Debroy - economist, PM's EAC member
    "rohlamba",          # Rohit Lamba - co-authored with Raghuram Rajan
    "pbmehta",           # Pratap Bhanu Mehta - CPR
    "DeveshKapur",       # Devesh Kapur - Johns Hopkins SAIS
    "ArvindSubramanian", # Arvind Subramanian - former CEA

    # Indian economy focused accounts
    "indianecomarket",   # Indian Economy & Market

    # Business news (for paper/research mentions)
    "livemint",          # Mint
    "EconomicTimes",     # Economic Times

    # Global economists who cover India
    "Msjenniferhunt",    # Jennifer Hunt - NBER
    "Eloloewenstein",    # Elora Loewenstein - econ research
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def parse_twitter_date(date_str: str) -> Optional[str]:
    """Parse RSS date to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        # feedparser usually provides struct_time via published_parsed
        dt = datetime(*date_str[:6])
        return dt.strftime("%Y-%m-%d")
    except:
        return None


class TwitterFetcher(BaseFetcher):
    """
    Fetcher for Twitter/X accounts via OpenRSS.

    Note: OpenRSS experimental Twitter feeds only capture tweets
    posted AFTER you first subscribe. Historical tweets are not available.
    This means the first run will likely return no results.
    """

    def __init__(self, accounts: list[str] = None):
        super().__init__("Twitter/X", "economics")
        self.accounts = accounts or ECON_ACCOUNTS

    def fetch(self) -> Iterator[Paper]:
        """Fetch tweets from monitored economics accounts."""
        seen_urls = set()

        for account in self.accounts:
            try:
                feed_url = f"{OPENRSS_BASE}{account}"

                response = requests.get(feed_url, headers=HEADERS, timeout=30)
                if response.status_code != 200:
                    print(f"    @{account}: HTTP {response.status_code}")
                    continue

                feed = feedparser.parse(response.content)

                if not feed.entries:
                    # Expected on first run - OpenRSS only gets new tweets
                    continue

                for entry in feed.entries:
                    # Get tweet content
                    title = entry.get('title', '')
                    content = entry.get('summary', '') or entry.get('description', '')
                    link = entry.get('link', '')

                    if not title or not link or link in seen_urls:
                        continue

                    seen_urls.add(link)

                    # Check if tweet mentions research/papers/economics
                    text = f"{title} {content}".lower()
                    research_keywords = [
                        'paper', 'research', 'study', 'findings', 'published',
                        'working paper', 'nber', 'ssrn', 'journal', 'review',
                        'economics', 'economic', 'gdp', 'inflation', 'monetary',
                        'fiscal', 'rbi', 'policy', 'trade', 'growth', 'data'
                    ]

                    # Skip tweets that don't mention research/economics
                    if not any(kw in text for kw in research_keywords):
                        continue

                    # Get date
                    date_text = None
                    if entry.get('published_parsed'):
                        date_text = parse_twitter_date(entry.published_parsed)

                    yield Paper(
                        title=f"@{account}: {title[:100]}..." if len(title) > 100 else f"@{account}: {title}",
                        authors=f"@{account}",
                        abstract=content[:500] if content else title,
                        url=link,
                        source="Twitter/X",
                        category="economics",
                        published_date=date_text,
                        is_india_specific=is_india_relevant(title, content)
                    )

            except Exception as e:
                print(f"    @{account}: Error - {e}")
                continue


# Convenience function
def get_twitter_fetcher():
    return TwitterFetcher()
