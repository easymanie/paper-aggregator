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
    JNUFetcher,
    CSEPFetcher,
    FICCIFetcher,
)
from .twitter import TwitterFetcher
from .kiel import KielFetcher
from .unctad import UNCTADFetcher
from .cag import CAGFetcher

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
    'JNUFetcher',
    'CSEPFetcher',
    'FICCIFetcher',
    'UNCTADFetcher',
    'CAGFetcher',
    'TwitterFetcher',
    'KielFetcher',
]
