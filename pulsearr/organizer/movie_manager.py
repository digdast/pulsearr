import os
import shutil
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from ..config import config
from ..database import get_db

logger = logging.getLogger("pulsearr.organizer.movies")

class MovieFileManager:
    @staticmethod
    def sanitize_filename(name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def format_movie_filename(
        self,
        format_template: str,
        movie_title: str,
        year: int,
        quality: str,
        extension: str = ".mkv"
    ) -> str:
        clean_title = self.sanitize_filename(movie_title)
        clean_quality = self.sanitize_filename(quality or "1080p")

        filename = format_template.format(
            **{
                "Movie Title": clean_title,
                "Year": year,
                "Quality": clean_quality
            }
        )
        if not filename.endswith(extension):
            filename += extension
        return self.sanitize_filename(filename)

    async def import_movie_download(
        self,
        queue_id: int,
        source_title: str,
        movie_id: int,
        quality: str,
        indexer: str,
        download_client: str,
        source_file_path: Optional[str] = None
    ) -> bool:
        """Handles post-download processing and file organization for movie releases."""
        async with get_db() as db:
            cursor = await db.execute("SELECT id, title, year, path FROM movies WHERE id = ?", (movie_id,))
            movie = await cursor.fetchone()
            if not movie:
                logger.error(f"Cannot import: Movie id {movie_id} not found.")
                return False

            movie_dir = Path(movie["path"])
            movie_dir.mkdir(parents=True, exist_ok=True)

            dest_filename = self.format_movie_filename(
                format_template="{Movie Title} ({Year}) [{Quality}]",
                movie_title=movie["title"],
                year=movie["year"],
                quality=quality,
                extension=".mkv"
            )
            dest_file_path = movie_dir / dest_filename

            if source_file_path and os.path.exists(source_file_path):
                if config.import_mode == "copy":
                    shutil.copy2(source_file_path, dest_file_path)
                elif config.import_mode == "hardlink":
                    try:
                        os.link(source_file_path, dest_file_path)
                    except Exception:
                        shutil.copy2(source_file_path, dest_file_path)
                else:  # move
                    shutil.move(source_file_path, dest_file_path)
                file_size = os.path.getsize(dest_file_path)
            else:
                # Mock movie media stream for virtual simulator
                with open(dest_file_path, "wb") as f:
                    f.write(b"PULSEARR_MOVIE_STREAM_MOCK_CONTAINER\x00\x00\x01\xba" + b"\x00" * 4096)
                file_size = 2450000000

            # Update movie in DB
            await db.execute(
                """
                UPDATE movies
                SET has_file = 1, file_path = ?, quality = ?, file_size = ?
                WHERE id = ?
                """,
                (str(dest_file_path), quality, file_size, movie["id"])
            )

            # Update queue item
            await db.execute("UPDATE queue SET status = 'completed', progress = 100.0 WHERE id = ?", (queue_id,))

            # Record in history
            await db.execute(
                """
                INSERT INTO history (
                    media_type, movie_id,
                    event_type, source_title, quality, indexer, download_client, path
                ) VALUES ('movie', ?, 'imported', ?, ?, ?, ?, ?)
                """,
                (
                    movie_id,
                    source_title,
                    quality,
                    indexer,
                    download_client,
                    str(dest_file_path)
                )
            )
            await db.commit()

        logger.info(f"Successfully imported movie '{dest_filename}' to '{dest_file_path}'")
        return True

movie_file_manager = MovieFileManager()
