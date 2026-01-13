"""Paper source fetchers."""

from .base import BaseFetcher, is_india_relevant
from .journals import JournalFetcher
from .nber import NBERFetcher
from .rbi import RBIFetcher, SEBIFetcher, NIPFPFetcher, NCAERFetcher
from .ssrn import SSRNFetcher

__all__ = [
    'BaseFetcher',
    'is_india_relevant',
    'JournalFetcher',
    'NBERFetcher',
    'RBIFetcher',
    'SEBIFetcher',
    'NIPFPFetcher',
    'NCAERFetcher',
    'SSRNFetcher',
]
