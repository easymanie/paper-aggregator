#!/usr/bin/env python3
"""Generate static HTML dashboard from the papers database."""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import db


def extract_doi(url: str) -> str:
    """Extract DOI from a URL if present."""
    if not url:
        return ""

    # Common DOI patterns in URLs
    patterns = [
        r'doi\.org/(10\.\d+/[^\s?#]+)',
        r'doi/(10\.\d+/[^\s?#]+)',
        r'(10\.\d+/[^\s?#&]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            doi = match.group(1)
            # Clean up trailing punctuation
            doi = doi.rstrip('.,;:')
            return doi

    return ""


def create_summary(abstract: str, max_chars: int = 250) -> str:
    """Create a 2-3 line summary from abstract."""
    if not abstract:
        return ""

    # Remove common prefixes
    prefixes = [
        r'^(RBI Working Paper|NIPFP Working Paper|NCAER Publication|SEBI Research):\s*',
        r'^Abstract[:\s]*',
    ]

    text = abstract
    for prefix in prefixes:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)

    # Clean up
    text = ' '.join(text.split())

    # Truncate to ~2-3 lines (around 250 chars)
    if len(text) <= max_chars:
        return text

    # Try to cut at sentence boundary
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    last_space = truncated.rfind(' ')

    if last_period > max_chars * 0.6:
        return truncated[:last_period + 1]
    elif last_space > 0:
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


def generate_dashboard(output_path: Path = None):
    """Generate the HTML dashboard."""

    if output_path is None:
        output_path = Path(__file__).parent / "output" / "index.html"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database if needed
    db.init_db()

    # Get data
    papers = db.get_all_papers()
    sources = db.get_sources()
    categories = db.get_categories()
    total_papers = db.get_paper_count()

    # Enrich papers with DOI and summary
    for paper in papers:
        paper['doi'] = extract_doi(paper.get('url', ''))
        paper['summary'] = create_summary(paper.get('abstract', ''))

    # Set up Jinja2
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html")

    # Render template
    html = template.render(
        papers=papers,
        sources=sources,
        categories=categories,
        total_papers=total_papers,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    # Write output
    output_path.write_text(html)
    print(f"Dashboard generated: {output_path}")

    return output_path


def open_dashboard(path: Path):
    """Open the dashboard in the default browser."""
    import platform

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(path)])
        elif system == "Windows":
            subprocess.run(["start", str(path)], shell=True)
        else:  # Linux and others
            subprocess.run(["xdg-open", str(path)])
    except Exception as e:
        print(f"Could not open browser: {e}")
        print(f"Please open manually: {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate the paper aggregator dashboard")
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="Open the dashboard in browser after generating"
    )
    parser.add_argument(
        "--output", "-O",
        type=Path,
        help="Output path for the HTML file"
    )

    args = parser.parse_args()

    path = generate_dashboard(args.output)

    if args.open:
        open_dashboard(path)


if __name__ == "__main__":
    main()
