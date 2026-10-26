import logging
from typing import List
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models import IndexerConfig
from ..indexers.torznab import TorznabIndexer
from ..indexers.eztv import EZTVIndexer

logger = logging.getLogger("pulsearr.api.indexers")
router = APIRouter(prefix="/indexers", tags=["Indexers"])

@router.get("", response_model=List[IndexerConfig])
async def list_indexers():
    """Lists all configured indexers."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM indexers ORDER BY priority ASC")
        rows = await cursor.fetchall()
        return [
            IndexerConfig(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                url=r["url"],
                api_key=r["api_key"],
                categories=r["categories"],
                enabled=bool(r["enabled"]),
                priority=r["priority"]
            )
            for r in rows
        ]

@router.post("", response_model=dict)
async def create_indexer(payload: IndexerConfig):
    """Creates a new indexer."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO indexers (name, type, url, api_key, categories, enabled, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.name, payload.type, payload.url, payload.api_key, payload.categories, 1 if payload.enabled else 0, payload.priority)
        )
        await db.commit()
        return {"id": cursor.lastrowid, "status": "created"}

@router.put("/{indexer_id}")
async def update_indexer(indexer_id: int, payload: IndexerConfig):
    """Updates an existing indexer."""
    async with get_db() as db:
        await db.execute(
            """
            UPDATE indexers
            SET name = ?, type = ?, url = ?, api_key = ?, categories = ?, enabled = ?, priority = ?
            WHERE id = ?
            """,
            (payload.name, payload.type, payload.url, payload.api_key, payload.categories, 1 if payload.enabled else 0, payload.priority, indexer_id)
        )
        await db.commit()
    return {"status": "updated"}

@router.delete("/{indexer_id}")
async def delete_indexer(indexer_id: int):
    """Deletes an indexer."""
    async with get_db() as db:
        await db.execute("DELETE FROM indexers WHERE id = ?", (indexer_id,))
        await db.commit()
    return {"status": "deleted"}

@router.post("/{indexer_id}/test")
async def test_indexer(indexer_id: int):
    """Tests connection to an indexer."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM indexers WHERE id = ?", (indexer_id,))
        r = await cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Indexer not found")

    itype = r["type"].lower()
    if itype in ("torznab", "newznab"):
        idx = TorznabIndexer(r["id"], r["name"], r["url"], r["api_key"], r["categories"])
    elif itype == "eztv":
        idx = EZTVIndexer(r["id"], r["name"], r["url"])
    else:
        return {"success": False, "message": f"Unsupported indexer type: {itype}"}

    success, msg = await idx.test_connection()
    return {"success": success, "message": msg}
