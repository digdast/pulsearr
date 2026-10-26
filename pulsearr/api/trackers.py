import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..indexers.manager import indexer_manager
from ..models import IndexerConfig

logger = logging.getLogger("pulsearr.api.trackers")
router = APIRouter(prefix="/trackers", tags=["Trackers (Prowlarr)"])

@router.get("", response_model=List[IndexerConfig])
async def list_trackers():
    """Returns all configured trackers/indexers with capabilities and latency."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM indexers ORDER BY priority ASC, name ASC")
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            results.append(IndexerConfig(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                url=r["url"],
                api_key=r["api_key"] or "",
                categories=r["categories"] or "5000",
                capabilities=r["capabilities"] if "capabilities" in r.keys() and r["capabilities"] else "both",
                enabled=bool(r["enabled"]),
                priority=r["priority"] or 1,
                latency_ms=r["latency_ms"] if "latency_ms" in r.keys() else 0
            ))
        return results

@router.post("/test-all")
async def test_all_trackers():
    """Runs parallel benchmark tests across all configured trackers (Prowlarr hub)."""
    benchmarks = await indexer_manager.benchmark_indexers()
    return {"status": "success", "benchmarks": benchmarks}
