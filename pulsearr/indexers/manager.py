import asyncio
import logging
import json
import time
from typing import List, Optional, Dict, Any
from .base import BaseIndexer
from .torznab import TorznabIndexer
from .eztv import EZTVIndexer
from .yts import YTSIndexer
from ..models import ReleaseCandidate, QualityProfile
from ..database import get_db

logger = logging.getLogger("pulsearr.indexers.manager")

class IndexerManager:
    async def get_enabled_indexers(self, media_type: str = "both") -> List[BaseIndexer]:
        """Loads and instantiates enabled indexers supporting the specified media type."""
        indexers = []
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT id, name, type, url, api_key, categories, capabilities FROM indexers WHERE enabled = 1 ORDER BY priority ASC"
            )
            rows = await cursor.fetchall()
            for r in rows:
                itype = r["type"].lower()
                caps = (r["capabilities"] or "both").lower()

                # Filter by media type
                if media_type == "tv" and caps == "movie":
                    continue
                if media_type == "movie" and caps == "tv":
                    continue

                if itype in ("torznab", "newznab"):
                    indexers.append(TorznabIndexer(r["id"], r["name"], r["url"], r["api_key"], r["categories"]))
                elif itype == "eztv":
                    indexers.append(EZTVIndexer(r["id"], r["name"], r["url"]))
                elif itype == "yts":
                    indexers.append(YTSIndexer(r["id"], r["name"], r["url"]))
        return indexers

    async def search_all(
        self,
        query: str,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        media_type: str = "tv",
        profile_id: int = 1
    ) -> List[ReleaseCandidate]:
        """Asynchronously queries all capable indexers in parallel."""
        indexers = await self.get_enabled_indexers(media_type=media_type)
        if not indexers:
            logger.info(f"No enabled indexers found for media_type='{media_type}'.")
            return []

        quality_profile = await self.get_profile(profile_id)

        tasks = [idx.search(query, season, episode) for idx in indexers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_candidates: List[ReleaseCandidate] = []
        seen_titles = set()

        for idx, res in zip(indexers, results):
            if isinstance(res, Exception):
                logger.error(f"Error querying indexer {idx.name}: {res}")
                continue
            for cand in res:
                if cand.title in seen_titles:
                    continue
                seen_titles.add(cand.title)
                
                # Check profile rules
                self.evaluate_candidate(cand, quality_profile)
                all_candidates.append(cand)

        # Sort: first by meets_cutoff/validity, then score, then seeders
        all_candidates.sort(
            key=lambda c: (
                0 if c.reject_reasons else 1,
                c.parsed.score,
                c.seeders or 0
            ),
            reverse=True
        )

        return all_candidates

    async def benchmark_indexers(self) -> List[Dict[str, Any]]:
        """Tests all indexers concurrently, measuring response latency in ms (Prowlarr hub)."""
        async with get_db() as db:
            cursor = await db.execute("SELECT id, name, type, url, api_key, categories FROM indexers")
            rows = await cursor.fetchall()

        benchmarks = []
        for r in rows:
            itype = r["type"].lower()
            if itype in ("torznab", "newznab"):
                idx = TorznabIndexer(r["id"], r["name"], r["url"], r["api_key"], r["categories"])
            elif itype == "eztv":
                idx = EZTVIndexer(r["id"], r["name"], r["url"])
            elif itype == "yts":
                idx = YTSIndexer(r["id"], r["name"], r["url"])
            else:
                continue

            start = time.time()
            success, msg = await idx.test_connection()
            latency = int((time.time() - start) * 1000) if success else 0

            # Update latency in DB
            async with get_db() as db:
                await db.execute(
                    "UPDATE indexers SET latency_ms = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
                    (latency, r["id"])
                )
                await db.commit()

            benchmarks.append({
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "success": success,
                "latency_ms": latency,
                "message": msg
            })

        return benchmarks

    async def fetch_all_rss(self) -> List[ReleaseCandidate]:
        """Fetches RSS from all enabled indexers concurrently."""
        indexers = await self.get_enabled_indexers(media_type="both")
        tasks = [idx.fetch_rss() for idx in indexers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates = []
        for idx, res in zip(indexers, results):
            if isinstance(res, Exception):
                logger.error(f"Error fetching RSS for {idx.name}: {res}")
                continue
            candidates.extend(res)
        return candidates

    async def get_profile(self, profile_id: int) -> Optional[QualityProfile]:
        async with get_db() as db:
            cursor = await db.execute("SELECT id, name, cutoff_id, items_json FROM quality_profiles WHERE id = ?", (profile_id,))
            row = await cursor.fetchone()
            if row:
                return QualityProfile(
                    id=row["id"],
                    name=row["name"],
                    cutoff_id=row["cutoff_id"],
                    items=json.loads(row["items_json"])
                )
        return None

    def evaluate_candidate(self, cand: ReleaseCandidate, profile: Optional[QualityProfile]):
        """Evaluates whether candidate meets quality profile criteria."""
        if not profile:
            return

        matched_item = None
        for item in profile.items:
            if item.resolution.lower() in cand.parsed.resolution.lower():
                if item.source.lower() in cand.parsed.source.lower():
                    matched_item = item
                    break

        if not matched_item:
            for item in profile.items:
                if item.resolution.lower() in cand.parsed.resolution.lower():
                    matched_item = item
                    break

        if matched_item:
            cand.parsed.score += matched_item.score
            if matched_item.min_size_mb and cand.size > 0 and cand.size < (matched_item.min_size_mb * 1024 * 1024):
                cand.reject_reasons.append(f"Size too small (< {matched_item.min_size_mb}MB)")
            if matched_item.max_size_mb and cand.size > (matched_item.max_size_mb * 1024 * 1024):
                cand.reject_reasons.append(f"Size too large (> {matched_item.max_size_mb}MB)")
        else:
            cand.reject_reasons.append(f"Quality '{cand.parsed.quality_tag}' not in profile '{profile.name}'")

indexer_manager = IndexerManager()
