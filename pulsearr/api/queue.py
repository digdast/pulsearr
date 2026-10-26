import logging
from typing import List
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models import QueueItemModel
from ..downloader.manager import download_manager
from ..organizer.file_manager import file_manager
from ..organizer.movie_manager import movie_file_manager

logger = logging.getLogger("pulsearr.api.queue")
router = APIRouter(prefix="/queue", tags=["Queue"])

@router.get("", response_model=List[QueueItemModel])
async def get_queue():
    """Returns active download queue items (supporting both TV shows and Movies)."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT q.*, s.title as series_title, m.title as movie_title
            FROM queue q
            LEFT JOIN series s ON s.id = q.series_id
            LEFT JOIN movies m ON m.id = q.movie_id
            WHERE q.status != 'completed'
            ORDER BY q.id DESC
            """
        )
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            results.append(QueueItemModel(
                id=r["id"],
                title=r["title"],
                media_type=r["media_type"] if "media_type" in r.keys() and r["media_type"] else "tv",
                series_id=r["series_id"],
                movie_id=r["movie_id"] if "movie_id" in r.keys() else None,
                season_number=r["season_number"],
                episode_number=r["episode_number"],
                download_client_id=r["download_client_id"],
                client_item_id=r["client_item_id"],
                protocol=r["protocol"],
                size=r["size"],
                status=r["status"],
                progress=r["progress"],
                download_speed=r["download_speed"],
                eta=r["eta"],
                quality=r["quality"],
                indexer=r["indexer"],
                download_url=r["download_url"],
                added_at=str(r["added_at"]),
                series_title=r["series_title"],
                movie_title=r["movie_title"]
            ))
        return results

@router.delete("/{queue_id}")
async def remove_from_queue(queue_id: int):
    """Cancels and removes download from queue and download client."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM queue WHERE id = ?", (queue_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Queue item not found")

        client = await download_manager.get_client(row["download_client_id"])
        if client:
            try:
                await client.remove(row["client_item_id"], delete_data=True)
            except Exception as e:
                logger.warning(f"Error removing item from client: {e}")

        await db.execute("DELETE FROM queue WHERE id = ?", (queue_id,))
        await db.commit()

    return {"status": "removed"}

@router.post("/{queue_id}/import")
async def force_import(queue_id: int):
    """Manually triggers import for queue item (TV or Movie)."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM queue WHERE id = ?", (queue_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Queue item not found")

    client = await download_manager.get_client(row["download_client_id"])
    client_name = client.name if client else "Manual"

    is_movie = (row["media_type"] == "movie" or bool(row["movie_id"])) if "media_type" in row.keys() else False

    if is_movie:
        success = await movie_file_manager.import_movie_download(
            queue_id=row["id"],
            source_title=row["title"],
            movie_id=row["movie_id"],
            quality=row["quality"],
            indexer=row["indexer"],
            download_client=client_name
        )
    else:
        success = await file_manager.import_download(
            queue_id=row["id"],
            source_title=row["title"],
            series_id=row["series_id"],
            season_number=row["season_number"],
            episode_number=row["episode_number"],
            quality=row["quality"],
            indexer=row["indexer"],
            download_client=client_name
        )

    if not success:
        raise HTTPException(status_code=500, detail="Import failed. Check logs.")
    return {"status": "imported"}
