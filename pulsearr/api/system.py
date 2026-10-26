import os
import sys
import shutil
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..config import DB_PATH, config
from ..database import get_db
from ..scheduler.engine import scheduler_engine

logger = logging.getLogger("pulsearr.api.system")
router = APIRouter(prefix="/system", tags=["System"])

@router.get("/status")
async def get_system_status():
    """Returns application health, resource metrics, and library statistics."""
    # Disk usage
    root_path = config.root_folder if os.path.exists(config.root_folder) else os.getcwd()
    total_b, used_b, free_b = shutil.disk_usage(root_path)

    # Database file size
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

    async with get_db() as db:
        c1 = await db.execute("SELECT COUNT(*) FROM series")
        series_count = (await c1.fetchone())[0]

        c2 = await db.execute("SELECT COUNT(*), COUNT(CASE WHEN has_file = 1 THEN 1 END) FROM episodes")
        r2 = await c2.fetchone()
        episodes_count = r2[0]
        downloaded_count = r2[1]

        c3 = await db.execute("SELECT COUNT(*), COUNT(CASE WHEN has_file = 1 THEN 1 END) FROM movies")
        r3 = await c3.fetchone()
        movies_count = r3[0]
        movies_downloaded = r3[1]

        c4 = await db.execute("SELECT COUNT(*) FROM queue WHERE status = 'downloading'")
        queue_count = (await c4.fetchone())[0]

    return {
        "version": config.version,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "disk": {
            "total_gb": round(total_b / (1024**3), 2),
            "free_gb": round(free_b / (1024**3), 2),
            "used_gb": round(used_b / (1024**3), 2),
            "percent_used": round((used_b / total_b) * 100, 1)
        },
        "database_size_kb": round(db_size / 1024, 2),
        "library": {
            "series": series_count,
            "episodes": episodes_count,
            "downloaded": downloaded_count,
            "movies": movies_count,
            "movies_downloaded": movies_downloaded,
            "queue_active": queue_count
        }
    }

@router.post("/rss-sync")
async def trigger_rss_sync():
    """Triggers an immediate manual RSS sync."""
    asyncio.create_task(scheduler_engine.sync_rss())
    return {"status": "sync_triggered"}

@router.get("/events")
async def sse_events():
    """Server-Sent Events endpoint for real-time frontend streaming."""
    async def event_generator():
        queue = await scheduler_engine.subscribe()
        try:
            # Send initial connected ping
            yield "event: ping\ndata: {\"status\":\"connected\"}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await scheduler_engine.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
