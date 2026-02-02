"""
Tracks topics and keywords The Daily Brief has already covered.
This is used to filter recommendations to avoid suggesting papers on topics already written about.
"""

# Keywords and topics extracted from The Daily Brief articles
# Updated: 2026-01-20

COVERED_TOPICS = [
    # Banking & RBI coverage (extensively covered)
    # Note: Be specific - don't flag broad topics, only specific stories covered
    "rbi rule change", "expected credit loss", "ecl framework", "bank provisioning",
    "rbi bulletin", "non-food credit", "bank lending slowdown",
    "rbi annual report", "corporate borrowing", "market-based funding",
    "indian banking 2025", "gross npa 2.2%", "bad loans multi-decade low",
    "rbi rate cuts 100 basis points", "monetary policy transmission",
    "acquisition financing", "leveraged buyout", "lbo", "bank m&a lending",
    "ipo financing limits", "lending against shares",

    # IPOs covered
    "meesho ipo", "meesho", "value commerce",
    "hdb financial ipo", "hdb financial", "hdfc bank nbfc",
    "amagi media labs ipo", "amagi",
    "shadowfax ipo", "shadowfax", "logistics ipo",

    # Markets & Trading
    "24-hour trading", "24x exchange", "stock market 24/7",
    "results season", "quarterly results",

    # Sectors covered
    "quick commerce", "10-minute delivery", "q-commerce",
    "ems business", "electronics manufacturing",
    "lab-grown diamonds", "titan diamonds", "de beers",
    "lab monkeys", "pharmaceutical testing",
    "venezuelan oil", "indian refineries", "oil imports",
    "coal ipo", "india coal",
    "nike", "just do it", "sportswear",

    # Macro/Economy
    "outlook 2026", "2026 predictions", "ten questions 2026",
    "india gdp 2025", "india growth forecast",
    "inflation cooling", "cpi inflation", "january inflation",
    "free trade agreements", "india uk fta", "india oman fta",
    "tariffs", "us tariffs india",

    # AI & Tech
    "us china ai", "ai competition", "hyperscalers", "ai infrastructure",

    # Microfinance
    "microfinance stress", "microfinance npa", "mfi portfolio",

    # Export incentives
    "export incentive scheme", "rodtep", "remission of duties",
]

# Article titles for exact matching
COVERED_ARTICLES = [
    "Can Shadowfax deliver?",
    "Just (can't) do it?",
    "What really separates US and Chinese AI",
    "Why Venezuelan oil needs Indian refineries",
    "Inside Amagi Media Labs IPO",
    "No middle ground in the EMS business",
    "Indian Banking in 2025: the year in review",
    "Outlook 2026",
    "Titan changes its mind about lab-grown diamonds",
    "Why are prices for lab monkeys suddenly rising?",
    "Is 10-Minute delivery just an Indian story?",
    "A new IPO lays out India's coal puzzle",
    "A small rule change by the RBI, a big leap for Indian banks",
    "RBI Bulletin: Interesting charts on the Indian economy",
    "The RBI just silently made some huge moves",
    "Digging through the RBI annual report",
    "Indian banks: a little cleaner, a little meaner",
    "What 2025 Holds for India's Economy and Markets",
    "How does one score the RBI?",
    "Big trends from this results season",
    "Indian banks want a shot at funding business takeovers",
    "Inside Meesho's IPO",
    "HDB Financial's IPO",
    "Stock Market 24/7: The future of trading is here!",
    "Ten Questions for 2026",
    "India's Inflation is Cooling Down",
]


def is_topic_covered(title: str, abstract: str) -> bool:
    """
    Check if a paper's topic has already been covered by The Daily Brief.
    Returns True if the topic appears to be already covered.
    """
    text = f"{title} {abstract}".lower()

    # Check against covered topics/keywords
    for topic in COVERED_TOPICS:
        if topic.lower() in text:
            return True

    # Check for similar article titles
    title_lower = title.lower()
    for article in COVERED_ARTICLES:
        # Check if significant words overlap
        article_words = set(article.lower().split())
        title_words = set(title_lower.split())
        # Remove common words
        common_words = {'the', 'a', 'an', 'in', 'on', 'of', 'for', 'to', 'and', 'is', 'are', 'was', 'were'}
        article_words -= common_words
        title_words -= common_words

        # If more than 50% of article words appear in title, likely covered
        if len(article_words) > 0:
            overlap = len(article_words & title_words) / len(article_words)
            if overlap > 0.5:
                return True

    return False


def get_coverage_penalty(title: str, abstract: str) -> int:
    """
    Return a penalty score if the topic is already covered.
    Higher penalty = less likely to be recommended.
    """
    if is_topic_covered(title, abstract):
        return -50  # Significant penalty for covered topics
    return 0
