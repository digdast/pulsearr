import os
import shutil
import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from ..models import SeriesModel, SeriesCreate, SeriesUpdate, SeasonModel, EpisodeModel
from ..metadata.tvmaze import tvmaze_client
from ..organizer.file_manager import file_manager
from ..config import config

logger = logging.getLogger("pulsearr.api.series")
router = APIRouter(prefix="/series", tags=["Series"])

@router.get("", response_model=List[SeriesModel])
async def list_series():
    """Lists all monitored TV series in library."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT s.*, 
                   COUNT(CASE WHEN e.has_file = 1 THEN 1 END) as downloaded_episode_count
            FROM series s
            LEFT JOIN episodes e ON e.series_id = s.id
            GROUP BY s.id
            ORDER BY s.sort_title ASC
            """
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            genres_list = json.loads(r["genres"]) if r["genres"] else []
            result.append(SeriesModel(
                id=r["id"],
                tvmaze_id=r["tvmaze_id"],
                title=r["title"],
                sort_title=r["sort_title"],
                status=r["status"],
                overview=r["overview"],
                poster_url=r["poster_url"],
                banner_url=r["banner_url"],
                network=r["network"],
                genres=genres_list,
                premiered=r["premiered"],
                path=r["path"],
                quality_profile_id=r["quality_profile_id"],
                monitored=bool(r["monitored"]),
                season_count=r["season_count"],
                episode_count=r["episode_count"],
                downloaded_episode_count=r["downloaded_episode_count"],
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"])
            ))
        return result

@router.get("/{series_id}")
async def get_series_detail(series_id: int):
    """Returns series detail including all seasons and episodes."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM series WHERE id = ?", (series_id,))
        series_row = await cursor.fetchone()
        if not series_row:
            raise HTTPException(status_code=404, detail="Series not found")

        # Get seasons
        cursor = await db.execute(
            "SELECT * FROM seasons WHERE series_id = ? ORDER BY season_number ASC",
            (series_id,)
        )
        seasons_rows = await cursor.fetchall()

        # Get episodes
        cursor = await db.execute(
            "SELECT * FROM episodes WHERE series_id = ? ORDER BY season_number ASC, episode_number ASC",
            (series_id,)
        )
        episodes_rows = await cursor.fetchall()

        episodes_by_season = {}
        for ep in episodes_rows:
            ep_model = {
                "id": ep["id"],
                "series_id": ep["series_id"],
                "season_id": ep["season_id"],
                "tvmaze_id": ep["tvmaze_id"],
                "season_number": ep["season_number"],
                "episode_number": ep["episode_number"],
                "title": ep["title"],
                "air_date": ep["air_date"],
                "overview": ep["overview"],
                "monitored": bool(ep["monitored"]),
                "has_file": bool(ep["has_file"]),
                "file_path": ep["file_path"],
                "quality": ep["quality"],
                "file_size": ep["file_size"],
                "created_at": str(ep["created_at"])
            }
            episodes_by_season.setdefault(ep["season_number"], []).append(ep_model)

        seasons_list = []
        for s in seasons_rows:
            s_num = s["season_number"]
            seasons_list.append({
                "id": s["id"],
                "series_id": s["series_id"],
                "season_number": s_num,
                "monitored": bool(s["monitored"]),
                "episode_count": s["episode_count"],
                "episodes": episodes_by_season.get(s_num, [])
            })

        genres_list = json.loads(series_row["genres"]) if series_row["genres"] else []
        return {
            "id": series_row["id"],
            "tvmaze_id": series_row["tvmaze_id"],
            "title": series_row["title"],
            "sort_title": series_row["sort_title"],
            "status": series_row["status"],
            "overview": series_row["overview"],
            "poster_url": series_row["poster_url"],
            "network": series_row["network"],
            "genres": genres_list,
            "premiered": series_row["premiered"],
            "path": series_row["path"],
            "quality_profile_id": series_row["quality_profile_id"],
            "monitored": bool(series_row["monitored"]),
            "season_count": series_row["season_count"],
            "episode_count": series_row["episode_count"],
            "seasons": seasons_list
        }

@router.post("", response_model=dict)
async def add_series(payload: SeriesCreate):
    """Adds a new series from TVMaze to the library."""
    # Check if already added
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM series WHERE tvmaze_id = ?", (payload.tvmaze_id,))
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="Series is already in library.")

    # Fetch complete metadata from TVMaze
    show_data = await tvmaze_client.get_show_details(payload.tvmaze_id)
    if not show_data:
        raise HTTPException(status_code=404, detail="Could not retrieve show metadata from TVMaze.")

    # Determine destination folder path
    title = show_data["title"]
    clean_title = file_manager.sanitize_filename(title)
    root_folder = payload.path or config.root_folder
    series_path = str(Path(root_folder) / clean_title)
    os.makedirs(series_path, exist_ok=True)

    sort_title = title.lower()
    for prefix in ["the ", "a ", "an "]:
        if sort_title.startswith(prefix):
            sort_title = sort_title[len(prefix):]
            break

    async with get_db() as db:
        # Insert series
        cursor = await db.execute(
            """
            INSERT INTO series (
                tvmaze_id, title, sort_title, status, overview, poster_url,
                network, genres, premiered, path, quality_profile_id, monitored,
                season_count, episode_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                show_data["tvmaze_id"],
                title,
                sort_title,
                show_data["status"],
                show_data["overview"],
                show_data["poster_url"],
                show_data["network"],
                json.dumps(show_data["genres"]),
                show_data["premiered"],
                series_path,
                payload.quality_profile_id,
                1 if payload.monitored else 0,
                show_data["season_count"],
                show_data["episode_count"]
            )
        )
        series_id = cursor.lastrowid

        # Insert seasons and episodes
        for s in show_data["seasons"]:
            s_cursor = await db.execute(
                """
                INSERT INTO seasons (series_id, season_number, monitored, episode_count)
                VALUES (?, ?, 1, ?)
                """,
                (series_id, s["season_number"], s["episode_count"])
            )
            season_id = s_cursor.lastrowid

            for ep in s["episodes"]:
                await db.execute(
                    """
                    INSERT INTO episodes (
                        series_id, season_id, tvmaze_id, season_number, episode_number,
                        title, air_date, overview, monitored, has_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
                    """,
                    (
                        series_id,
                        season_id,
                        ep["tvmaze_id"],
                        ep["season_number"],
                        ep["episode_number"],
                        ep["title"],
                        ep["air_date"],
                        ep["overview"]
                    )
                )

        await db.commit()

    # Trigger disk scan in case files already exist in path
    try:
        await file_manager.scan_series_folder(series_id)
    except Exception as e:
        logger.warning(f"Initial disk scan failed: {e}")

    logger.info(f"Added series '{title}' (ID: {series_id}) with {show_data['episode_count']} episodes.")
    return {"id": series_id, "title": title, "path": series_path, "status": "success"}

@router.put("/{series_id}")
async def update_series(series_id: int, payload: SeriesUpdate):
    """Updates series settings."""
    async with get_db() as db:
        updates = []
        params = []
        if payload.monitored is not None:
            updates.append("monitored = ?")
            params.append(1 if payload.monitored else 0)
        if payload.quality_profile_id is not None:
            updates.append("quality_profile_id = ?")
            params.append(payload.quality_profile_id)
        if payload.path is not None:
            updates.append("path = ?")
            params.append(payload.path)

        if updates:
            params.append(series_id)
            await db.execute(f"UPDATE series SET {', '.join(updates)} WHERE id = ?", params)
            await db.commit()

    return {"status": "updated"}

@router.delete("/{series_id}")
async def delete_series(series_id: int, delete_files: bool = Query(False)):
    """Deletes series from library and optionally deletes files on disk."""
    async with get_db() as db:
        cursor = await db.execute("SELECT title, path FROM series WHERE id = ?", (series_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Series not found")

        path = row["path"]
        await db.execute("DELETE FROM series WHERE id = ?", (series_id,))
        await db.commit()

    if delete_files and path and os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception as e:
            logger.error(f"Error removing files for series {series_id}: {e}")

    return {"status": "deleted"}

@router.post("/{series_id}/scan")
async def scan_series(series_id: int):
    """Triggers disk scan for series."""
    matched = await file_manager.scan_series_folder(series_id)
    return {"status": "success", "matched_files": matched}
