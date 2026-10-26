from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from ..models import ReleaseCandidate

class BaseIndexer(ABC):
    def __init__(self, id: int, name: str, url: str, api_key: str = "", categories: str = "5000"):
        self.id = id
        self.name = name
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.categories = categories

    @abstractmethod
    async def search(self, query: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[ReleaseCandidate]:
        """Search indexer for specific series/season/episode."""
        pass

    @abstractmethod
    async def fetch_rss(self) -> List[ReleaseCandidate]:
        """Fetch latest releases from indexer RSS feed."""
        pass

    @abstractmethod
    async def test_connection(self) -> Tuple[bool, str]:
        """Test connection to indexer."""
        pass
