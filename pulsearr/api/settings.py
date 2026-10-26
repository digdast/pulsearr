import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from ..config import config, DEFAULT_ROOT_FOLDER
from ..database import get_db
from ..organizer.file_manager import file_manager
from ..organizer.movie_manager import movie_file_manager

logger = logging.getLogger("pulsearr.api.settings")
router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsUpdate(BaseModel):
    root_folder: str
    movies_root_folder: Optional[str] = None
    standard_episode_format: str
    standard_movie_format: Optional[str] = "{Movie Title} ({Year}) [{Quality}]"
    import_mode: str
    auto_import: bool
    rename_episodes: bool

class PreviewFormatPayload(BaseModel):
    format_template: str
    media_type: str = "tv"
    series_title: str = "Severance"
    season: int = 2
    episode: int = 1
    episode_title: str = "Hello Kier"
    quality: str = "WEB-DL-1080p"
    movie_title: str = "Inception"
    year: int = 2010

@router.get("")
async def get_settings():
    """Returns application configuration settings for TV and Movies."""
    default_movie_root = str(Path(DEFAULT_ROOT_FOLDER).parent / "movies")
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        db_settings = {r["key"]: r["value"] for r in rows}

    return {
        "root_folder": db_settings.get("root_folder", config.root_folder),
        "movies_root_folder": db_settings.get("movies_root_folder", default_movie_root),
        "standard_episode_format": db_settings.get("standard_episode_format", config.standard_episode_format),
        "standard_movie_format": db_settings.get("standard_movie_format", "{Movie Title} ({Year}) [{Quality}]"),
        "import_mode": db_settings.get("import_mode", config.import_mode),
        "auto_import": db_settings.get("auto_import", "true") == "true",
        "rename_episodes": db_settings.get("rename_episodes", "true") == "true",
        "api_key": config.api_key,
        "port": config.port,
        "version": config.version
    }

@router.post("")
async def update_settings(payload: SettingsUpdate):
    """Updates application settings in database and runtime config."""
    config.root_folder = payload.root_folder
    config.standard_episode_format = payload.standard_episode_format
    config.import_mode = payload.import_mode
    config.auto_import = payload.auto_import
    config.rename_episodes = payload.rename_episodes

    default_movie_root = str(Path(DEFAULT_ROOT_FOLDER).parent / "movies")
    movie_root = payload.movies_root_folder or default_movie_root
    movie_fmt = payload.standard_movie_format or "{Movie Title} ({Year}) [{Quality}]"

    async with get_db() as db:
        for k, v in [
            ("root_folder", payload.root_folder),
            ("movies_root_folder", movie_root),
            ("standard_episode_format", payload.standard_episode_format),
            ("standard_movie_format", movie_fmt),
            ("import_mode", payload.import_mode),
            ("auto_import", "true" if payload.auto_import else "false"),
            ("rename_episodes", "true" if payload.rename_episodes else "false")
        ]:
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))
        await db.commit()

    return {"status": "updated"}

@router.post("/preview-format")
async def preview_format(payload: PreviewFormatPayload):
    """Previews an episode or movie filename formatting template."""
    if payload.media_type == "movie":
        preview = movie_file_manager.format_movie_filename(
            format_template=payload.format_template,
            movie_title=payload.movie_title,
            year=payload.year,
            quality=payload.quality
        )
    else:
        preview = file_manager.format_episode_filename(
            format_template=payload.format_template,
            series_title=payload.series_title,
            season_num=payload.season,
            episode_num=payload.episode,
            episode_title=payload.episode_title,
            quality=payload.quality
        )
    return {"preview": preview}
