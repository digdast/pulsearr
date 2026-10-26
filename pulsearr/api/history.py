import logging
from typing import List
from fastapi import APIRouter, Query
from ..database import get_db
from ..models import HistoryItemModel

logger = logging.getLogger("pulsearr.api.history")
router = APIRouter(prefix="/history", tags=["History"])

@router.get("", response_model=List[HistoryItemModel])
async def get_history(limit: int = Query(50, le=200)):
    """Returns recent grab, import, and download history events for TV and Movies."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT h.*, s.title as series_title, m.title as movie_title
            FROM history h
            LEFT JOIN series s ON s.id = h.series_id
            LEFT JOIN movies m ON m.id = h.movie_id
            ORDER BY h.id DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            results.append(HistoryItemModel(
                id=r["id"],
                media_type=r["media_type"] if "media_type" in r.keys() and r["media_type"] else "tv",
                series_id=r["series_id"],
                movie_id=r["movie_id"] if "movie_id" in r.keys() else None,
                season_number=r["season_number"],
                episode_number=r["episode_number"],
                event_type=r["event_type"],
                source_title=r["source_title"],
                quality=r["quality"],
                indexer=r["indexer"],
                download_client=r["download_client"],
                path=r["path"],
                timestamp=str(r["timestamp"]),
                series_title=r["series_title"],
                movie_title=r["movie_title"]
            ))
        return results
