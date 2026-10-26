import json
import logging
from typing import List
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models import QualityProfile

logger = logging.getLogger("pulsearr.api.profiles")
router = APIRouter(prefix="/profiles", tags=["Quality Profiles"])

@router.get("", response_model=List[QualityProfile])
async def list_profiles():
    """Returns available quality profiles."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM quality_profiles ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [
            QualityProfile(
                id=r["id"],
                name=r["name"],
                cutoff_id=r["cutoff_id"],
                items=json.loads(r["items_json"])
            )
            for r in rows
        ]

@router.put("/{profile_id}")
async def update_profile(profile_id: int, payload: QualityProfile):
    """Updates a quality profile."""
    async with get_db() as db:
        await db.execute(
            """
            UPDATE quality_profiles
            SET name = ?, cutoff_id = ?, items_json = ?
            WHERE id = ?
            """,
            (payload.name, payload.cutoff_id, json.dumps([item.model_dump() for item in payload.items]), profile_id)
        )
        await db.commit()
    return {"status": "updated"}
