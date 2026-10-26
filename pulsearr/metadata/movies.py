import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pulsearr.metadata.movies")

YTS_MIRRORS = [
    "https://yts.lt",
    "https://yts.bz",
    "https://yts.mx"
]

class MovieMetadataClient:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    async def search_movies(self, query: str) -> List[Dict[str, Any]]:
        """Searches for movies using public movie endpoints with fallback."""
        clean_q = query.strip()
        cache_key = f"movie_search:{clean_q.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        movies_results = []
        for mirror in YTS_MIRRORS:
            try:
                url = f"{mirror}/api/v2/list_movies.json"
                async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                    resp = await client.get(url, params={"query_term": clean_q, "limit": 20})
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_list = data.get("data", {}).get("movies", [])
                        for m in raw_list:
                            poster = m.get("large_cover_image") or m.get("medium_cover_image") or ""
                            movies_results.append({
                                "title": m.get("title"),
                                "year": int(m.get("year") or 0),
                                "imdb_id": m.get("imdb_code"),
                                "tmdb_id": None,
                                "overview": m.get("summary") or m.get("synopsis") or "",
                                "poster_url": poster,
                                "banner_url": m.get("background_image_original") or m.get("background_image") or "",
                                "genres": m.get("genres") or [],
                                "rating": float(m.get("rating") or 0.0),
                                "runtime": int(m.get("runtime") or 0)
                            })
                        if movies_results:
                            break
            except Exception as e:
                logger.debug(f"Movie search failed on mirror {mirror}: {e}")
                continue

        self._cache[cache_key] = movies_results
        return movies_results

movie_metadata_client = MovieMetadataClient()
