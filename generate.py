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


def classify_topic(title: str, abstract: str) -> list[str]:
    """
    Classify paper into topic categories based on keywords.
    Returns list of matching topics (a paper can have multiple topics).
    """
    text = f"{title} {abstract}".lower()
    topics = []

    # Topic definitions with keywords
    topic_keywords = {
        "Monetary Policy": [
            'monetary policy', 'interest rate', 'inflation', 'central bank', 'rbi',
            'reserve bank', 'repo rate', 'liquidity', 'money supply', 'quantitative easing',
            'currency', 'exchange rate', 'forex', 'rupee', 'depreciation', 'appreciation'
        ],
        "Fiscal Policy": [
            'fiscal policy', 'fiscal deficit', 'budget', 'government spending',
            'public debt', 'government debt', 'taxation', 'tax reform', 'gst',
            'subsidy', 'public finance', 'sovereign', 'debt sustainability'
        ],
        "Trade & FDI": [
            'trade policy', 'export', 'import', 'tariff', 'fdi', 'foreign direct investment',
            'foreign investment', 'trade deficit', 'current account', 'wto', 'bilateral trade',
            'trade agreement', 'globalization', 'supply chain', 'global value chain'
        ],
        "Banking & Finance": [
            'banking', 'bank', 'credit', 'loan', 'npa', 'non-performing', 'financial market',
            'capital market', 'stock market', 'equity', 'bond', 'mutual fund', 'insurance',
            'fintech', 'payment', 'upi', 'digital payment', 'financial inclusion',
            'microfinance', 'nbfc', 'sebi', 'nse', 'bse', 'ipo', 'securities'
        ],
        "Labor & Employment": [
            'labor', 'labour', 'employment', 'unemployment', 'wage', 'job', 'worker',
            'workforce', 'informal sector', 'gig economy', 'skill', 'human capital',
            'migration', 'remittance', 'labor market', 'minimum wage'
        ],
        "Development": [
            'poverty', 'inequality', 'development', 'gdp', 'economic growth', 'per capita',
            'living standard', 'welfare', 'social protection', 'inclusive growth',
            'sustainable development', 'sdg', 'middle income'
        ],
        "Corporate & Management": [
            'corporate', 'firm', 'company', 'governance', 'board', 'ceo', 'shareholder',
            'merger', 'acquisition', 'm&a', 'startup', 'entrepreneur', 'sme', 'msme',
            'business', 'strategy', 'competition', 'market structure', 'productivity'
        ],
        "Environment & Energy": [
            'climate', 'carbon', 'emission', 'green', 'renewable', 'solar', 'wind',
            'energy', 'electricity', 'coal', 'oil', 'gas', 'pollution', 'environmental',
            'sustainability', 'net zero', 'paris agreement', 'esg'
        ],
        "Education": [
            'education', 'school', 'college', 'university', 'student', 'teacher',
            'literacy', 'enrollment', 'dropout', 'learning', 'higher education',
            'vocational', 'skill development', 'academic'
        ],
        "Health": [
            'health', 'healthcare', 'hospital', 'medical', 'disease', 'mortality',
            'morbidity', 'nutrition', 'sanitation', 'pharmaceutical', 'drug',
            'vaccine', 'covid', 'pandemic', 'insurance health'
        ],
        "Agriculture & Rural": [
            'agriculture', 'farm', 'farmer', 'crop', 'food', 'rural', 'msp',
            'procurement', 'irrigation', 'land', 'agrarian', 'agri', 'livestock',
            'dairy', 'fishery', 'food security', 'pds'
        ],
        "Infrastructure": [
            'infrastructure', 'road', 'highway', 'railway', 'port', 'airport',
            'transport', 'logistics', 'construction', 'real estate', 'housing',
            'urban', 'smart city', 'metro', 'connectivity'
        ],
        "Technology & Digital": [
            'technology', 'digital', 'internet', 'broadband', 'telecom', 'ai',
            'artificial intelligence', 'machine learning', 'automation', 'robot',
            'data', 'e-commerce', 'platform', 'it sector', 'software', 'startup tech'
        ],
    }

    # Check each topic
    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in text:
                topics.append(topic)
                break  # One match is enough for this topic

    # If no topics matched, classify as "General Economics"
    if not topics:
        topics = ["General Economics"]

    return topics


def calculate_relevance_score(title: str, abstract: str, category: str, source: str) -> int:
    """
    Calculate relevance score for economics/finance focus.
    Higher score = more relevant to core econ/finance.
    Returns score from 0-100.
    """
    text = f"{title} {abstract}".lower()
    score = 50  # Base score

    # High relevance keywords (core economics/finance) +15 each
    high_relevance = [
        'gdp', 'inflation', 'monetary policy', 'fiscal policy', 'interest rate',
        'central bank', 'rbi', 'reserve bank', 'sebi', 'stock market', 'equity',
        'bond', 'credit', 'banking', 'financial market', 'capital market',
        'trade deficit', 'current account', 'foreign exchange', 'forex', 'rupee',
        'investment', 'portfolio', 'asset price', 'liquidity', 'monetary',
        'macroeconomic', 'microeconomic', 'econometric', 'regression',
        'price', 'pricing', 'valuation', 'returns', 'volatility', 'risk premium',
        'nifty', 'sensex', 'bse', 'nse', 'ipo', 'fdi', 'fii', 'mutual fund',
        'corporate finance', 'capital structure', 'dividend', 'earnings',
        'profit', 'revenue', 'market efficiency', 'arbitrage', 'derivative',
        'option', 'futures', 'hedge', 'swap', 'yield', 'coupon', 'treasury',
        'fiscal deficit', 'government debt', 'public debt', 'taxation', 'gst',
        'tariff', 'export', 'import', 'trade policy', 'wto', 'bilateral trade',
    ]

    # Medium relevance keywords (business/management) +8 each
    medium_relevance = [
        'firm', 'company', 'enterprise', 'startup', 'entrepreneur', 'sme',
        'industry', 'manufacturing', 'service sector', 'productivity',
        'efficiency', 'performance', 'growth', 'development', 'strategy',
        'competition', 'market share', 'innovation', 'technology', 'digital',
        'supply chain', 'logistics', 'operations', 'management', 'governance',
        'board', 'ceo', 'executive', 'shareholder', 'stakeholder', 'merger',
        'acquisition', 'm&a', 'restructuring', 'bankruptcy', 'insolvency',
        'regulation', 'compliance', 'policy reform', 'liberalization',
        'privatization', 'subsidy', 'incentive', 'economic zone', 'corridor',
    ]

    # Lower relevance keywords (sociology-leaning) -10 each
    low_relevance = [
        'caste', 'gender equality', 'social identity', 'ethnicity', 'religion',
        'discrimination', 'inequality', 'marginalized', 'vulnerable', 'tribal',
        'dalit', 'backward class', 'reservation', 'affirmative action',
        'migration', 'diaspora', 'refugee', 'displacement', 'resettlement',
        'health outcome', 'mortality', 'morbidity', 'nutrition', 'sanitation',
        'education access', 'literacy', 'school enrollment', 'dropout',
        'child', 'adolescent', 'elderly', 'aging', 'demographic transition',
        'household survey', 'ethnographic', 'qualitative study', 'interview',
        'focus group', 'participatory', 'community-based', 'grassroots',
        'ngo', 'civil society', 'activism', 'social movement', 'protest',
        'environmental justice', 'climate vulnerability', 'disaster',
        'cultural', 'tradition', 'ritual', 'marriage', 'kinship', 'family',
    ]

    # Count matches
    for kw in high_relevance:
        if kw in text:
            score += 15

    for kw in medium_relevance:
        if kw in text:
            score += 8

    for kw in low_relevance:
        if kw in text:
            score -= 10

    # Category bonus
    if category == 'finance':
        score += 20
    elif category == 'economics':
        score += 15
    elif category == 'management':
        score += 10
    elif category == 'policy':
        score += 5

    # Source bonus (Indian policy/finance institutions)
    high_value_sources = ['RBI', 'SEBI', 'NIPFP', 'NCAER', 'IGIDR', 'NBER']
    if source in high_value_sources:
        score += 10

    # Topic-based adjustments (applied after classification)
    # This will be handled separately in generate_dashboard

    # Clamp score to 0-100
    return max(0, min(100, score))


def calculate_daily_brief_score(paper: dict) -> int:
    """
    Calculate how suitable a paper is for The Daily Brief.
    Based on: topic relevance, source credibility, recency, content quality,
    and whether the topic has already been covered.
    """
    from daily_brief_coverage import get_coverage_penalty, is_topic_covered

    score = 0
    title = paper.get('title', '')
    abstract = paper.get('abstract', '')
    source = paper.get('source', '')
    topics = paper.get('topics', [])
    text = f"{title} {abstract}"

    # Check if topic already covered - apply penalty
    coverage_penalty = get_coverage_penalty(title, abstract)
    score += coverage_penalty

    # Store coverage status for display
    paper['is_covered'] = is_topic_covered(title, abstract)

    title = title.lower()
    abstract = abstract.lower()

    # 1. Source credibility bonus (official/academic sources preferred)
    credible_sources = {
        'RBI': 40,           # Official central bank - highest credibility
        'SEBI': 35,          # Markets regulator
        'NIPFP': 30,         # Top policy think tank
        'NCAER': 30,         # Economic research
        'NBER': 35,          # Top global working papers
        'IGIDR': 25,         # Academic institution
        'ISI Delhi': 25,     # Statistical research
        'ICRIER': 25,        # Trade/economic research
        'CPR': 20,           # Policy research
    }
    score += credible_sources.get(source, 10)

    # 2. Topic alignment with Daily Brief coverage
    db_topics = ['Banking & Finance', 'Monetary Policy', 'Fiscal Policy',
                 'Trade & FDI', 'Corporate & Management', 'Technology & Digital',
                 'Infrastructure']
    for t in topics:
        if t in db_topics:
            score += 15

    # 3. Story-worthy keywords (things that make good narratives)
    story_keywords = [
        'india', 'indian', 'rbi', 'sebi', 'nifty', 'sensex', 'rupee',
        'bank', 'credit', 'loan', 'npa', 'fintech', 'upi', 'digital payment',
        'inflation', 'interest rate', 'monetary policy', 'gdp', 'growth',
        'trade', 'export', 'import', 'fdi', 'tariff',
        'startup', 'ipo', 'equity', 'stock', 'market',
        'corporate', 'firm', 'company', 'governance',
        'policy', 'reform', 'regulation', 'gst',
        'energy', 'coal', 'oil', 'renewable', 'green',
        'manufacturing', 'services', 'employment', 'wage',
    ]
    keyword_matches = sum(1 for kw in story_keywords if kw in text)
    score += min(keyword_matches * 3, 30)  # Cap at 30

    # 4. Recency bonus
    from datetime import datetime
    pub_date = paper.get('published_date')
    if pub_date:
        try:
            dt = datetime.strptime(pub_date, '%Y-%m-%d')
            days_old = (datetime.now() - dt).days
            if days_old < 30:
                score += 25  # Very recent
            elif days_old < 90:
                score += 15  # Recent
            elif days_old < 180:
                score += 5   # Moderately recent
        except:
            pass

    # 5. Title quality (shorter, punchier titles often better for stories)
    title_len = len(paper.get('title', ''))
    if 30 <= title_len <= 100:
        score += 5  # Good length

    # 6. Penalty for overly academic/niche topics
    niche_keywords = ['ethnographic', 'anthropological', 'qualitative study',
                      'focus group', 'participatory', 'grassroots']
    if any(kw in text for kw in niche_keywords):
        score -= 15

    return max(0, score)


def calculate_daily_brief_fit_score(paper: dict) -> int:
    """
    Calculate how well a paper fits The Daily Brief editorial style.

    Based on analysis of actual Daily Brief stories, they cover:
    1. IPOs, company analysis, business models, unit economics
    2. RBI/SEBI policy with direct market/banking impact
    3. Banking, credit, NPAs, financial system stories
    4. Stock market, capital markets, M&A, trading
    5. Geopolitical events with India business angle
    6. Industry disruption and transformation stories

    They do NOT typically cover:
    - Pure academic/theoretical research
    - Environmental/sustainability papers without business angle
    - Health, education policy papers
    - Development economics without market relevance
    """
    title = paper.get('title', '').lower()
    abstract = paper.get('abstract', '').lower()
    source = paper.get('source', '')
    text = f"{title} {abstract}"

    score = 0

    # STRONG POSITIVE: Core Daily Brief topics

    # IPO/Company analysis keywords (+30 each)
    ipo_keywords = ['ipo', 'initial public offering', 'listing', 'going public',
                    'business model', 'unit economics', 'profitability', 'margins',
                    'revenue growth', 'market share', 'competitive advantage']
    for kw in ipo_keywords:
        if kw in text:
            score += 30

    # RBI/SEBI/Central bank policy (+25 each)
    policy_keywords = ['rbi', 'reserve bank', 'sebi', 'monetary policy', 'repo rate',
                       'interest rate cut', 'rate hike', 'inflation target', 'mpc',
                       'regulatory change', 'policy reform', 'npa', 'bad loan',
                       'capital adequacy', 'liquidity', 'forex reserve']
    for kw in policy_keywords:
        if kw in text:
            score += 25

    # Banking/Financial system (+20 each)
    banking_keywords = ['bank', 'banking sector', 'credit growth', 'deposit',
                        'lending', 'loan', 'nbfc', 'financial inclusion',
                        'digital payment', 'upi', 'fintech', 'insurance']
    for kw in banking_keywords:
        if kw in text:
            score += 20

    # Stock market/Capital markets (+20 each)
    market_keywords = ['stock market', 'equity', 'nifty', 'sensex', 'bse', 'nse',
                       'mutual fund', 'fii', 'dii', 'market cap', 'valuation',
                       'trading', 'investor', 'shareholder', 'dividend',
                       'm&a', 'merger', 'acquisition', 'takeover']
    for kw in market_keywords:
        if kw in text:
            score += 20

    # Company/Industry stories (+15 each)
    company_keywords = ['company', 'firm', 'corporate', 'startup', 'unicorn',
                        'reliance', 'tata', 'adani', 'infosys', 'hdfc', 'icici',
                        'industry', 'sector', 'market leader', 'disruption']
    for kw in company_keywords:
        if kw in text:
            score += 15

    # Trade/Geopolitical with business angle (+15 each)
    trade_keywords = ['tariff', 'trade war', 'export', 'import', 'fdi',
                      'foreign investment', 'supply chain', 'manufacturing',
                      'china', 'us', 'oil price', 'crude', 'commodity']
    for kw in trade_keywords:
        if kw in text:
            score += 15

    # NEGATIVE: Topics Daily Brief typically avoids

    # Environmental/Sustainability without business angle (-20 each)
    env_keywords = ['emission', 'carbon', 'climate change', 'sustainable development',
                    'environmental impact', 'pollution', 'green transition',
                    'renewable energy', 'solar panel', 'wind energy', 'esg']
    env_count = sum(1 for kw in env_keywords if kw in text)
    # Only penalize if no business keywords present
    if env_count > 0 and score < 30:
        score -= env_count * 20

    # Academic/Theoretical papers (-15 each)
    academic_keywords = ['theoretical framework', 'literature review', 'empirical analysis',
                         'regression', 'econometric', 'hypothesis', 'methodology',
                         'sample size', 'statistical significance', 'p-value']
    for kw in academic_keywords:
        if kw in text:
            score -= 15

    # Development/Social topics without market angle (-15 each)
    dev_keywords = ['poverty alleviation', 'social welfare', 'rural development',
                    'education policy', 'health outcome', 'gender equality',
                    'inequality', 'marginalized', 'vulnerable population']
    for kw in dev_keywords:
        if kw in text:
            score -= 15

    # Source-based adjustments
    # High-value sources for Daily Brief
    if source == 'RBI':
        score += 40  # RBI papers are always relevant
    elif source == 'SEBI':
        score += 35
    elif source in ['NBER', 'Quarterly Journal of Economics']:
        score += 25  # Top economics research
    elif source in ['NIPFP', 'NCAER']:
        score += 15  # Policy think tanks
    elif source in ['IGIDR', 'ISI Delhi']:
        score += 5   # Academic but sometimes relevant

    # Penalize sources that tend to be more academic/development focused
    if source in ['CPR', 'Ashoka CEDA']:
        # These often have good policy papers but also lots of development/social papers
        if score < 20:
            score -= 10

    # Editorial/non-paper content penalty
    if 'editorial' in title or 'editor' in title:
        score -= 100

    return max(-50, score)  # Floor at -50


def get_topic_priority_score(topics: list[str]) -> int:
    """
    Calculate priority score based on topics.
    Higher = more relevant to core econ/finance/management.
    """
    # Topic priority: positive = boost, negative = demote
    topic_priorities = {
        # Core economics/finance/business - HIGH priority
        "Monetary Policy": 20,
        "Fiscal Policy": 20,
        "Banking & Finance": 20,
        "Trade & FDI": 20,
        "Corporate & Management": 20,
        "Technology & Digital": 20,
        "General Economics": 15,

        # Development/Infrastructure/Labor - MEDIUM priority
        "Development": 10,
        "Infrastructure": 10,
        "Labor & Employment": 10,
        "Agriculture & Rural": 5,

        # Less core to daily business coverage - LOWER priority
        "Environment & Energy": -5,
        "Education": -10,
        "Health": -15,
    }

    # Take the highest priority among all topics
    if not topics:
        return 0

    return max(topic_priorities.get(t, 0) for t in topics)


def is_open_access(source: str, url: str = "") -> bool:
    """
    Determine if a paper is likely free/open access based on source.
    Returns True for open access, False for paywalled.
    """
    # Open access sources (institutional working papers, policy documents)
    open_access_sources = {
        'RBI',           # Central bank - all public
        'SEBI',          # Regulator - all public
        'NIPFP',         # Think tank working papers
        'NCAER',         # Think tank working papers
        'NBER',          # Working papers (free access)
        'ICRIER',        # Think tank working papers
        'CPR',           # Think tank working papers
        'Ashoka CEDA',   # University working papers
        'IIM Ahmedabad', # University working papers
        'IGIDR',         # University working papers
        'ISI Delhi',     # University working papers
        'Vikalpa',       # Open access journal
        'IIMB Management Review',  # Open access
    }

    if source in open_access_sources:
        return True

    # Check URL patterns for open access
    if url:
        open_access_patterns = [
            'nber.org',
            'rbi.org.in',
            'sebi.gov.in',
            'nipfp.org.in',
            'ncaer.org',
            'icrier.org',
            'cprindia.org',
            'ashoka.edu.in',
            'iima.ac.in',
            'igidr.ac.in',
            'isid.ac.in',
            'ideas.repec.org',  # Working paper repository
        ]
        for pattern in open_access_patterns:
            if pattern in url.lower():
                return True

    # Most journal sources are paywalled
    return False


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


def create_summary(abstract: str, max_chars: int = 280) -> str:
    """Create a meaningful 2-3 line summary from abstract."""
    if not abstract:
        return ""

    text = abstract

    # Check if abstract is ONLY metadata (no actual content after journal info)
    # Pattern: "Journal Name, Volume X, Issue Y, Page X-Y, Month Year." with nothing else
    metadata_only = re.match(
        r'^[A-Za-z\s&\-]+,\s*(Volume|Vol\.?)\s*\d+,\s*(Issue|No\.?)\s*\d+,?\s*(Page|Pages|pp\.?)?\s*[\d\-]*,?\s*[A-Za-z\-]*\s*\d{0,4}\.?\s*$',
        abstract.strip(),
        re.IGNORECASE
    )
    if metadata_only:
        return ""  # Will be handled by template as "Click to read full paper"

    # Remove common prefixes and metadata patterns
    removal_patterns = [
        r'^(RBI Working Paper|NIPFP Working Paper|NCAER Publication|SEBI Research|IGIDR Working Paper|ISI Delhi Discussion Paper|CPR Working Paper|ICRIER Working Paper|Ashoka University CEDA|IIM Ahmedabad Working Paper):\s*',
        r'^Abstract[:\s]*',
        r'^Summary[:\s]*',
        # Remove journal metadata like "Journal Name, Volume X, Issue Y, Page..."
        r'^[A-Za-z\s&]+,\s*(Volume|Vol\.?)\s*\d+,\s*(Issue|No\.?)\s*\d+,\s*(Page|Pages|pp\.?)\s*[\d\-]+,?\s*[A-Za-z]*\s*\d{4}\.?\s*',
        r'^[A-Za-z\s&]+,\s*EarlyView\.?\s*',
        r'^[A-Za-z\s&]+,\s*Ahead of Print\.?\s*',
        # Remove "Publication date: Month Year Source: Journal..."
        r'^Publication date:\s*[A-Za-z]+\s*\d{4}\s*Source:\s*[^\.]+\.\s*',
        r'^Publication date:\s*[A-Za-z]+\s*\d{4}[^\.]*\.\s*',
        # Remove author listings at start
        r'^Author\(s\):\s*[^\.]+\.\s*',
    ]

    for pattern in removal_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Also remove journal metadata that appears mid-text
    text = re.sub(r'Vikalpa,\s*Volume\s*\d+,\s*Issue\s*\d+,\s*Page\s*[\d\-]+,\s*[A-Za-z\-]+\.?\s*', '', text)
    text = re.sub(r'[A-Za-z\s&]+,\s*Volume\s*\d+,\s*Issue\s*\d+,\s*[A-Za-z]+\s*\d{4}\.?\s*', '', text)

    # Clean up whitespace
    text = ' '.join(text.split()).strip()

    # If text is too short after cleaning, it was mostly metadata
    if len(text) < 50:
        return ""

    # Try to find the most informative sentences
    # Look for sentences with key phrases that indicate findings/conclusions
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Priority keywords that indicate important content
    priority_keywords = [
        'we find', 'we show', 'results suggest', 'findings indicate',
        'this paper', 'this study', 'we examine', 'we analyze', 'we investigate',
        'evidence suggests', 'results show', 'data shows', 'analysis reveals',
        'conclude', 'implication', 'impact', 'effect', 'significant',
        'increase', 'decrease', 'growth', 'decline', 'change'
    ]

    # Score sentences by importance
    scored_sentences = []
    for i, sent in enumerate(sentences):
        score = 0
        sent_lower = sent.lower()

        # Boost for priority keywords
        for kw in priority_keywords:
            if kw in sent_lower:
                score += 2

        # Boost for being early in abstract (usually contains key info)
        if i < 2:
            score += 1

        # Penalty for very short sentences
        if len(sent) < 40:
            score -= 1

        scored_sentences.append((score, sent))

    # Sort by score and build summary
    scored_sentences.sort(key=lambda x: -x[0])

    summary = ""
    for score, sent in scored_sentences:
        if len(summary) + len(sent) + 1 <= max_chars:
            summary = (summary + " " + sent).strip() if summary else sent
        elif not summary:
            # If first sentence is too long, truncate it
            summary = sent[:max_chars-3] + "..."
            break

    # If we still have no good summary, just use the beginning
    if not summary and text:
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        last_space = truncated.rfind(' ')
        if last_period > max_chars * 0.5:
            return truncated[:last_period + 1]
        elif last_space > 0:
            return truncated[:last_space] + "..."
        return truncated + "..."

    return summary


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

    # Enrich papers with DOI, summary, relevance score, and topics
    all_topics = set()
    for paper in papers:
        paper['doi'] = extract_doi(paper.get('url', ''))
        paper['summary'] = create_summary(paper.get('abstract', ''))
        paper['relevance_score'] = calculate_relevance_score(
            paper.get('title', ''),
            paper.get('abstract', ''),
            paper.get('category', ''),
            paper.get('source', '')
        )
        paper['topics'] = classify_topic(
            paper.get('title', ''),
            paper.get('abstract', '')
        )
        paper['topic_priority'] = get_topic_priority_score(paper['topics'])
        paper['daily_brief_score'] = calculate_daily_brief_score(paper)
        paper['daily_brief_fit'] = calculate_daily_brief_fit_score(paper)
        paper['is_open_access'] = is_open_access(paper.get('source', ''), paper.get('url', ''))
        all_topics.update(paper['topics'])

    # Sort topics alphabetically for the filter dropdown
    all_topics = sorted(all_topics)

    # Sort by:
    # 1. Daily Brief fit score (how well it matches DB editorial style)
    # 2. Date (most recent first)
    # 3. Open access (free papers first)
    def get_sort_date(p):
        date_str = p.get('published_date') or p.get('fetched_date') or '1900-01-01'
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').timestamp()
        except ValueError:
            return 0

    papers.sort(key=lambda p: (
        -p.get('daily_brief_fit', 0),         # Daily Brief editorial fit first
        -get_sort_date(p),                    # Then most recent first
        -int(p.get('is_open_access', False)), # Then free papers before paywalled
    ))

    # Set up Jinja2
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html")

    # Render template
    html = template.render(
        papers=papers,
        sources=sources,
        categories=categories,
        topics=all_topics,
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
