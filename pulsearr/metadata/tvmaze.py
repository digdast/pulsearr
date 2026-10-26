import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pulsearr.metadata.tvmaze")

class TVMazeClient:
    BASE_URL = "https://api.tvmaze.com"
    
    def __init__(self):
        # High performance client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"User-Agent": "Pulsearr/1.0 (Next-Gen Fast TV PVR)"}
        )
        self._cache: Dict[str, Any] = {}

    async def search_shows(self, query: str) -> List[Dict[str, Any]]:
        """Searches TVMaze for TV shows matching query."""
        cache_key = f"search:{query.lower().strip()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            resp = await self.client.get("/search/shows", params={"q": query})
            if resp.status_code != 200:
                logger.error(f"TVMaze search failed: {resp.status_code}")
                return []
                
            raw_results = resp.json()
            results = []
            for item in raw_results:
                show = item.get("show", {})
                if not show or not show.get("id"):
                    continue
                    
                image = show.get("image") or {}
                network = show.get("network") or show.get("webChannel") or {}
                
                results.append({
                    "tvmaze_id": show.get("id"),
                    "title": show.get("name", "Unknown Title"),
                    "status": show.get("status", "Unknown"),
                    "overview": show.get("summary", ""),
                    "poster_url": image.get("original") or image.get("medium") or "",
                    "network": network.get("name", "Unknown Network"),
                    "genres": show.get("genres", []),
                    "premiered": show.get("premiered") or "",
                    "rating": (show.get("rating") or {}).get("average")
                })
                
            self._cache[cache_key] = results
            return results
        except Exception as e:
            logger.exception(f"Error querying TVMaze search: {e}")
            return []

    async def get_show_details(self, tvmaze_id: int) -> Optional[Dict[str, Any]]:
        """Fetches full show metadata including all seasons and episodes."""
        cache_key = f"show:{tvmaze_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            resp = await self.client.get(
                f"/shows/{tvmaze_id}",
                params={"embed[]": ["episodes", "seasons"]}
            )
            if resp.status_code != 200:
                logger.error(f"Failed to fetch show {tvmaze_id}: {resp.status_code}")
                return None
                
            data = resp.json()
            embedded = data.get("_embedded", {})
            raw_episodes = embedded.get("episodes", [])
            raw_seasons = embedded.get("seasons", [])
            image = data.get("image") or {}
            network = data.get("network") or data.get("webChannel") or {}

            # Process seasons
            seasons_dict = {}
            for s in raw_seasons:
                s_num = s.get("number")
                if s_num is not None:
                    seasons_dict[s_num] = {
                        "season_number": s_num,
                        "episode_count": s.get("episodeOrder") or 0,
                        "premiere_date": s.get("premiereDate"),
                        "end_date": s.get("endDate"),
                        "episodes": []
                    }

            # Process episodes
            processed_episodes = []
            for ep in raw_episodes:
                s_num = ep.get("season")
                ep_num = ep.get("number")
                if s_num is None or ep_num is None:
                    continue
                    
                ep_data = {
                    "tvmaze_id": ep.get("id"),
                    "season_number": s_num,
                    "episode_number": ep_num,
                    "title": ep.get("name") or f"Episode {ep_num}",
                    "air_date": ep.get("airdate") or ep.get("airstamp", "")[:10] if ep.get("airstamp") else None,
                    "overview": ep.get("summary") or ""
                }
                processed_episodes.append(ep_data)
                
                if s_num in seasons_dict:
                    seasons_dict[s_num]["episodes"].append(ep_data)
                else:
                    seasons_dict[s_num] = {
                        "season_number": s_num,
                        "episode_count": 1,
                        "episodes": [ep_data]
                    }

            # Update actual episode counts in seasons
            for s_num, s_val in seasons_dict.items():
                s_val["episode_count"] = len(s_val["episodes"])

            show_data = {
                "tvmaze_id": data.get("id"),
                "title": data.get("name"),
                "status": data.get("status", "Unknown"),
                "overview": data.get("summary") or "",
                "poster_url": image.get("original") or image.get("medium") or "",
                "network": network.get("name", "Unknown Network"),
                "genres": data.get("genres", []),
                "premiered": data.get("premiered") or "",
                "seasons": sorted(seasons_dict.values(), key=lambda x: x["season_number"]),
                "episodes": processed_episodes,
                "season_count": len(seasons_dict),
                "episode_count": len(processed_episodes)
            }
            
            self._cache[cache_key] = show_data
            return show_data
        except Exception as e:
            logger.exception(f"Error fetching show details for {tvmaze_id}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

tvmaze_client = TVMazeClient()
