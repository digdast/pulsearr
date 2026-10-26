import os
import shutil
import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from ..models import MovieModel, MovieCreate, MovieUpdate
from ..metadata.movies import movie_metadata_client
from ..organizer.movie_manager import movie_file_manager
from ..config import config, DEFAULT_ROOT_FOLDER

logger = logging.getLogger("pulsearr.api.movies")
router = APIRouter(prefix="/movies", tags=["Movies (Radarr)"])

@router.get("", response_model=List[MovieModel])
async def list_movies():
    """Lists all movies in the library."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM movies ORDER BY sort_title ASC")
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            genres_list = json.loads(r["genres"]) if r["genres"] else []
            result.append(MovieModel(
                id=r["id"],
                tmdb_id=r["tmdb_id"],
                imdb_id=r["imdb_id"],
                title=r["title"],
                sort_title=r["sort_title"],
                year=r["year"],
                overview=r["overview"],
                poster_url=r["poster_url"],
                banner_url=r["banner_url"],
                genres=genres_list,
                runtime=r["runtime"] or 0,
                rating=float(r["rating"] or 0.0),
                path=r["path"],
                quality_profile_id=r["quality_profile_id"],
                monitored=bool(r["monitored"]),
                has_file=bool(r["has_file"]),
                file_path=r["file_path"],
                quality=r["quality"],
                file_size=r["file_size"] or 0,
                release_date=r["release_date"],
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"])
            ))
        return result

@router.get("/lookup")
async def lookup_movies(q: str = Query(..., min_length=1)):
    """Search for movie metadata across public movie databases."""
    results = await movie_metadata_client.search_movies(q)
    return results

@router.get("/{movie_id}", response_model=MovieModel)
async def get_movie(movie_id: int):
    """Returns movie details."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        r = await cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Movie not found")
        genres_list = json.loads(r["genres"]) if r["genres"] else []
        return MovieModel(
            id=r["id"],
            tmdb_id=r["tmdb_id"],
            imdb_id=r["imdb_id"],
            title=r["title"],
            sort_title=r["sort_title"],
            year=r["year"],
            overview=r["overview"],
            poster_url=r["poster_url"],
            banner_url=r["banner_url"],
            genres=genres_list,
            runtime=r["runtime"] or 0,
            rating=float(r["rating"] or 0.0),
            path=r["path"],
            quality_profile_id=r["quality_profile_id"],
            monitored=bool(r["monitored"]),
            has_file=bool(r["has_file"]),
            file_path=r["file_path"],
            quality=r["quality"],
            file_size=r["file_size"] or 0,
            release_date=r["release_date"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"])
        )

@router.post("", response_model=dict)
async def add_movie(payload: MovieCreate):
    """Adds a new movie to the monitored library."""
    clean_title = movie_file_manager.sanitize_filename(payload.title)
    
    # Resolve movies root directory
    async with get_db() as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'movies_root_folder'")
        row = await cursor.fetchone()
        root_dir = row["value"] if row else str(Path(DEFAULT_ROOT_FOLDER).parent / "movies")

    movie_path = payload.path or str(Path(root_dir) / f"{clean_title} ({payload.year})")
    os.makedirs(movie_path, exist_ok=True)

    sort_title = payload.title.lower()
    for prefix in ["the ", "a ", "an "]:
        if sort_title.startswith(prefix):
            sort_title = sort_title[len(prefix):]
            break

    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO movies (
                tmdb_id, imdb_id, title, sort_title, year, overview, poster_url,
                genres, runtime, rating, path, quality_profile_id, monitored
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.tmdb_id,
                payload.imdb_id,
                payload.title,
                sort_title,
                payload.year,
                payload.overview,
                payload.poster_url,
                json.dumps(payload.genres),
                payload.runtime or 0,
                payload.rating or 0.0,
                movie_path,
                payload.quality_profile_id,
                1 if payload.monitored else 0
            )
        )
        movie_id = cursor.lastrowid
        await db.commit()

    logger.info(f"Added movie '{payload.title} ({payload.year})' (ID: {movie_id})")
    return {"id": movie_id, "title": payload.title, "path": movie_path, "status": "success"}

@router.put("/{movie_id}")
async def update_movie(movie_id: int, payload: MovieUpdate):
    """Updates movie monitoring, profile, or path."""
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
            params.append(movie_id)
            await db.execute(f"UPDATE movies SET {', '.join(updates)} WHERE id = ?", params)
            await db.commit()

    return {"status": "updated"}

@router.delete("/{movie_id}")
async def delete_movie(movie_id: int, delete_files: bool = Query(False)):
    """Deletes a movie from library and optionally deletes files from disk."""
    async with get_db() as db:
        cursor = await db.execute("SELECT title, path FROM movies WHERE id = ?", (movie_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Movie not found")
        path = row["path"]
        await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await db.commit()

    if delete_files and path and os.path.exists(path):
        try:
            shutil.rmtree(path)
        except Exception as e:
            logger.error(f"Error removing files for movie {movie_id}: {e}")

    return {"status": "deleted"}
