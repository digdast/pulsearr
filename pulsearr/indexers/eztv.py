import logging
import re
import httpx
from typing import List, Optional, Tuple, Dict
from .base import BaseIndexer
from ..models import ReleaseCandidate
from ..parser.release_parser import release_parser

logger = logging.getLogger("pulsearr.indexers.eztv")

# Popular active EZTV mirrors for reliable fallback
EZTV_MIRRORS = [
    "https://eztvx.to",
    "https://eztv.re",
    "https://eztv.wf",
    "https://eztv.tf"
]

class EZTVIndexer(BaseIndexer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._imdb_cache: Dict[str, str] = {}

    async def _resolve_imdb_id(self, query: str) -> Optional[str]:
        """Resolves an IMDB ID from query string using TVMaze or regex."""
        clean_q = query.strip()
        
        # 1. Direct IMDB ID pattern: tt1234567 or 1234567
        if re.match(r'^(?:tt)?(\d{6,9})$', clean_q, re.IGNORECASE):
            match = re.match(r'^(?:tt)?(\d{6,9})$', clean_q, re.IGNORECASE)
            return match.group(1)

        # 2. Check local in-memory cache
        q_key = clean_q.lower()
        if q_key in self._imdb_cache:
            return self._imdb_cache[q_key]

        # 3. Query TVMaze API for external IMDB ID
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    "https://api.tvmaze.com/singlesearch/shows",
                    params={"q": clean_q}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    imdb_str = data.get("externals", {}).get("imdb")
                    if imdb_str:
                        num = imdb_str.replace("tt", "").strip()
                        self._imdb_cache[q_key] = num
                        logger.info(f"Resolved IMDB ID for '{clean_q}': {num}")
                        return num
        except Exception as e:
            logger.warning(f"Could not resolve IMDB ID for '{clean_q}': {e}")

        return None

    async def _fetch(self, params: dict) -> List[ReleaseCandidate]:
        """Queries EZTV API with automatic mirror fallback and resilience."""
        candidates = []
        raw_torrents = []
        
        # Primary base url
        base_urls = [self.url] if self.url and self.url != "https://eztvx.to/api/get-torrents" else []
        for m in EZTV_MIRRORS:
            full = f"{m}/api/get-torrents"
            if full not in base_urls:
                base_urls.append(full)

        last_err = None
        for base in base_urls:
            try:
                async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                    resp = await client.get(base, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_torrents = data.get("torrents", [])
                        break
                    else:
                        logger.warning(f"EZTV mirror {base} returned HTTP {resp.status_code}")
            except Exception as e:
                last_err = e
                continue

        if not raw_torrents and last_err:
            logger.warning(f"Failed to fetch from all EZTV mirrors: {last_err}")
            return []

        for t in raw_torrents:
            title = t.get("title") or t.get("filename")
            if not title:
                continue

            download_url = t.get("magnet_url") or t.get("torrent_url") or ""
            if not download_url:
                continue

            size = int(t.get("size_bytes") or 0)
            seeders = int(t.get("seeds") or 0)
            leechers = int(t.get("peers") or 0)

            # Parse title
            parsed = release_parser.parse(title)

            # Supplement season/episode from EZTV metadata if title didn't specify
            try:
                eztv_s = int(t.get("season", 0))
                eztv_ep = int(t.get("episode", 0))
                if parsed.season is None and eztv_s > 0:
                    parsed.season = eztv_s
                if parsed.episode is None and eztv_ep > 0:
                    parsed.episode = eztv_ep
                elif eztv_ep == 0 and eztv_s > 0:
                    parsed.season_pack = True
            except (ValueError, TypeError):
                pass

            candidate = ReleaseCandidate(
                guid=f"eztv-{t.get('id')}",
                indexer_id=self.id,
                indexer_name=self.name,
                title=title,
                download_url=download_url,
                protocol="torrent",
                size=size,
                seeders=seeders,
                leechers=leechers,
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
        """Searches EZTV for specific TV show, season, and episode."""
        imdb_num = await self._resolve_imdb_id(query)
        candidates = []

        if imdb_num:
            # Query by exact show IMDB ID
            params = {"imdb_id": imdb_num, "limit": 100, "page": 1}
            candidates = await self._fetch(params)

            # If searching for an episode and not found on page 1, fetch page 2
            if season is not None and episode is not None:
                has_ep = any(
                    (c.parsed.season == season and (c.parsed.episode == episode or c.parsed.season_pack))
                    for c in candidates
                )
                if not has_ep and len(candidates) >= 100:
                    params["page"] = 2
                    page2_candidates = await self._fetch(params)
                    candidates.extend(page2_candidates)
        else:
            # Fallback to recent torrents and filter by title words
            params = {"limit": 100}
            candidates = await self._fetch(params)

        # Filter precision matching
        filtered = []
        clean_words = [w.lower() for w in re.split(r'[\s._\-]+', query) if len(w) > 1]

        for cand in candidates:
            # If we queried by exact IMDB ID, title is already matched by IMDB
            # Otherwise, check all query words are present
            if not imdb_num:
                cand_title_lower = cand.title.lower()
                if not all(word in cand_title_lower for word in clean_words):
                    continue

            # Season filter
            if season is not None and cand.parsed.season is not None:
                if cand.parsed.season != season:
                    continue

            # Episode filter (allow exact episode or full season pack)
            if episode is not None and cand.parsed.episode is not None:
                if cand.parsed.episode != episode and not cand.parsed.season_pack:
                    continue

            filtered.append(cand)

        return filtered

    async def fetch_rss(self) -> List[ReleaseCandidate]:
        """Fetches the latest site-wide releases for RSS synchronization."""
        return await self._fetch({"limit": 100})

    async def test_connection(self) -> Tuple[bool, str]:
        """Tests connectivity against EZTV API mirrors."""
        for mirror in EZTV_MIRRORS:
            try:
                url = f"{mirror}/api/get-torrents"
                async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                    resp = await client.get(url, params={"limit": 1})
                    if resp.status_code == 200:
                        return True, f"EZTV is online and reachable ({mirror})."
            except Exception:
                continue

        return False, "Failed to connect to any EZTV mirrors."
