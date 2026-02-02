"""Paper source fetchers."""

from .base import BaseFetcher, is_india_relevant
from .journals import JournalFetcher
from .nber import NBERFetcher
from .rbi import RBIFetcher, SEBIFetcher, NIPFPFetcher, NCAERFetcher
from .ssrn import SSRNFetcher
from .thinktanks import (
    ICRIERFetcher,
    CPRFetcher,
    AshokaFetcher,
    IIMAFetcher,
    IGIDRFetcher,
    ISIFetcher,
    XKDRFetcher,
)
from .twitter import TwitterFetcher
from .kiel import KielFetcher

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
    'ICRIERFetcher',
    'CPRFetcher',
    'AshokaFetcher',
    'IIMAFetcher',
    'IGIDRFetcher',
    'ISIFetcher',
    'XKDRFetcher',
    'TwitterFetcher',
    'KielFetcher',
]
