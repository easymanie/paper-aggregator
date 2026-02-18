#!/usr/bin/env python3
"""Main script to fetch papers from all configured sources."""

import argparse
import sys
from pathlib import Path

import yaml

import db
from sources import (
    JournalFetcher,
    NBERFetcher,
    RBIFetcher,
    SEBIFetcher,
    NIPFPFetcher,
    NCAERFetcher,
    SSRNFetcher,
    ICRIERFetcher,
    CPRFetcher,
    AshokaFetcher,
    IIMAFetcher,
    IGIDRFetcher,
    ISIFetcher,
    XKDRFetcher,
    JNUFetcher,
    CSEPFetcher,
    FICCIFetcher,
    UNCTADFetcher,
    CAGFetcher,
    TwitterFetcher,
    KielFetcher,
)


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"

    if not config_path.exists():
        print(f"Warning: config.yaml not found at {config_path}")
        return {"journals": [], "scraped_sources": []}

    with open(config_path) as f:
        return yaml.safe_load(f)


def fetch_journals(config: dict) -> int:
    """Fetch papers from configured journal RSS feeds."""
    total = 0

    journals = config.get("journals", [])
    print(f"\nFetching from {len(journals)} journal feeds...")

    for journal in journals:
        name = journal.get("name", "Unknown")
        url = journal.get("url", "")
        category = journal.get("category", "economics")
        india_only = journal.get("india_only", True)

        if not url:
            print(f"  Skipping {name}: no URL configured")
            continue

        print(f"  {name}...", end=" ", flush=True)

        try:
            fetcher = JournalFetcher(name, url, category, india_only)
            count = 0

            for paper in fetcher.fetch():
                if db.insert_paper(paper):
                    count += 1

            print(f"{count} new papers")
            total += count

        except Exception as e:
            print(f"Error: {e}")

    return total


def fetch_scraped_sources(config: dict) -> int:
    """Fetch papers from scraped sources (RBI, SEBI, etc.)."""
    total = 0

    scraped = config.get("scraped_sources", [])
    print(f"\nFetching from {len(scraped)} institutional sources...")

    fetcher_map = {
        "RBI": RBIFetcher,
        "SEBI": SEBIFetcher,
        "NIPFP": NIPFPFetcher,
        "NCAER": NCAERFetcher,
        "NBER": NBERFetcher,
        "SSRN": SSRNFetcher,
        "ICRIER": ICRIERFetcher,
        "CPR": CPRFetcher,
        "Ashoka CEDA": AshokaFetcher,
        "IIM Ahmedabad": IIMAFetcher,
        "IGIDR": IGIDRFetcher,
        "ISI Delhi": ISIFetcher,
        "XKDR": XKDRFetcher,
        "JNU": JNUFetcher,
        "CSEP": CSEPFetcher,
        "FICCI": FICCIFetcher,
        "UNCTAD": UNCTADFetcher,
        "CAG": CAGFetcher,
        "Twitter/X": TwitterFetcher,
        "Kiel Institute": KielFetcher,
    }

    for source in scraped:
        name = source.get("name", "")
        enabled = source.get("enabled", True)

        if not enabled:
            print(f"  Skipping {name} (disabled)")
            continue

        if name not in fetcher_map:
            print(f"  Skipping {name}: no fetcher available")
            continue

        print(f"  {name}...", end=" ", flush=True)

        try:
            fetcher = fetcher_map[name]()
            count = 0

            for paper in fetcher.fetch():
                if db.insert_paper(paper):
                    count += 1

            print(f"{count} new papers")
            total += count

        except Exception as e:
            print(f"Error: {e}")

    return total


def main():
    parser = argparse.ArgumentParser(description="Fetch papers from all configured sources")
    parser.add_argument(
        "--journals-only",
        action="store_true",
        help="Only fetch from journal RSS feeds"
    )
    parser.add_argument(
        "--sources-only",
        action="store_true",
        help="Only fetch from scraped sources (RBI, SEBI, etc.)"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate dashboard after fetching"
    )

    args = parser.parse_args()

    # Initialize database
    print("Initializing database...")
    db.init_db()

    # Load config
    config = load_config()

    total = 0

    # Fetch from configured sources
    if not args.sources_only:
        total += fetch_journals(config)

    if not args.journals_only:
        total += fetch_scraped_sources(config)

    # Summary
    print(f"\n{'='*50}")
    print(f"Fetch complete: {total} new papers added")
    print(f"Total papers in database: {db.get_paper_count()}")

    # Generate dashboard if requested
    if args.generate:
        print("\nGenerating dashboard...")
        from generate import generate_dashboard
        generate_dashboard()


if __name__ == "__main__":
    main()
