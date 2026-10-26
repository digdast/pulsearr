import logging
import httpx
from typing import List, Optional, Tuple
from .base import BaseIndexer
from ..models import ReleaseCandidate
from ..parser.release_parser import release_parser

logger = logging.getLogger("pulsearr.indexers.yts")

YTS_API_MIRRORS = [
    "https://yts.lt/api/v2",
    "https://yts.bz/api/v2",
    "https://yts.mx/api/v2"
]

class YTSIndexer(BaseIndexer):
    """Direct fast movie indexer powered by YTS API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _fetch(self, endpoint: str, params: dict) -> List[ReleaseCandidate]:
        candidates = []
        raw_movies = []

        base_urls = [self.url] if self.url and "yts" in self.url else []
        for m in YTS_API_MIRRORS:
            if m not in base_urls:
                base_urls.append(m)

        for base in base_urls:
            try:
                async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                    resp = await client.get(f"{base}/{endpoint}", params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_movies = data.get("data", {}).get("movies", [])
                        break
            except Exception:
                continue

        for m in raw_movies:
            movie_title = m.get("title", "")
            movie_year = m.get("year", "")
            torrents = m.get("torrents", [])

            for t in torrents:
                quality = t.get("quality", "1080p")
                video_type = t.get("type", "bluray").upper()
                size_bytes = int(t.get("size_bytes") or 0)
                seeds = int(t.get("seeds") or 0)
                peers = int(t.get("peers") or 0)
                torrent_hash = t.get("hash", "")
                
                # Construct release title e.g. Inception.2010.1080p.BluRay.x264-YTS
                rel_title = f"{movie_title.replace(' ', '.')}.{movie_year}.{quality}.{video_type}.x264-YTS"
                
                # Construct magnet link
                magnet_url = (
                    f"magnet:?xt=urn:btih:{torrent_hash}"
                    f"&dn={rel_title}"
                    f"&tr=udp://tracker.opentrackr.org:1337/announce"
                    f"&tr=udp://open.stealth.si:80/announce"
                    f"&tr=udp://tracker.torrent.eu.org:451/announce"
                )

                parsed = release_parser.parse(rel_title)
                candidate = ReleaseCandidate(
                    guid=f"yts-{torrent_hash}",
                    indexer_id=self.id,
                    indexer_name=self.name,
                    title=rel_title,
                    download_url=magnet_url,
                    protocol="torrent",
                    size=size_bytes,
                    seeders=seeds,
                    leechers=peers,
                    parsed=parsed
                )
                candidates.append(candidate)

        return candidates

    async def search(
        self,
        query: str,
        season: Optional[int] = None,
        episode: Optional[int] = None
    ) -> List[ReleaseCandidate]:
        """Searches YTS for movie releases."""
        params = {"query_term": query.strip(), "limit": 20}
        return await self._fetch("list_movies.json", params)

    async def fetch_rss(self) -> List[ReleaseCandidate]:
        """Fetches newly uploaded movies from YTS."""
        return await self._fetch("list_movies.json", {"limit": 50, "sort_by": "date_added"})

    async def test_connection(self) -> Tuple[bool, str]:
        for base in YTS_API_MIRRORS:
            try:
                async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                    resp = await client.get(f"{base}/list_movies.json", params={"limit": 1})
                    if resp.status_code == 200:
                        return True, f"YTS Movie Tracker is online ({base})."
            except Exception:
                continue
        return False, "Failed to connect to YTS Movie Tracker."
