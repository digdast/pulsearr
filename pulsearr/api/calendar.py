import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from ..database import get_db

logger = logging.getLogger("pulsearr.api.calendar")
router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("")
async def get_calendar(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Returns calendar of upcoming and past TV show episodes within date window."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT e.*, s.title as series_title, s.poster_url, s.network
            FROM episodes e
            JOIN series s ON s.id = e.series_id
            WHERE e.air_date IS NOT NULL 
              AND e.air_date >= ? 
              AND e.air_date <= ?
            ORDER BY e.air_date ASC, s.title ASC
            """,
            (start_date, end_date)
        )
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "series_id": r["series_id"],
                "series_title": r["series_title"],
                "poster_url": r["poster_url"],
                "network": r["network"],
                "season_number": r["season_number"],
                "episode_number": r["episode_number"],
                "title": r["title"],
                "air_date": r["air_date"],
                "overview": r["overview"],
                "has_file": bool(r["has_file"]),
                "monitored": bool(r["monitored"])
            })
        return results
