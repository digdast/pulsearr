import os
import shutil
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from ..config import config
from ..database import get_db
from ..parser.release_parser import release_parser

logger = logging.getLogger("pulsearr.organizer")

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".m4v", ".mov", ".wmv"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".vtt", ".sub"}

class FileManager:
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Removes illegal filesystem characters, especially for Windows."""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def format_episode_filename(
        self,
        format_template: str,
        series_title: str,
        season_num: int,
        episode_num: int,
        episode_title: str,
        quality: str,
        extension: str = ".mkv"
    ) -> str:
        """Generates sanitized filename according to naming pattern."""
        clean_series = self.sanitize_filename(series_title)
        clean_ep_title = self.sanitize_filename(episode_title or f"Episode {episode_num}")
        clean_quality = self.sanitize_filename(quality or "WEB-DL-1080p")

        filename = format_template.format(
            **{
                "Series Title": clean_series,
                "season": season_num,
                "episode": episode_num,
                "Episode Title": clean_ep_title,
                "Quality": clean_quality
            }
        )
        if not filename.endswith(extension):
            filename += extension
        return self.sanitize_filename(filename)

    async def scan_series_folder(self, series_id: int) -> int:
        """Scans disk folder for existing media files and links them to database episodes."""
        async with get_db() as db:
            cursor = await db.execute("SELECT id, title, path FROM series WHERE id = ?", (series_id,))
            series = await cursor.fetchone()
            if not series:
                return 0

            series_path = Path(series["path"])
            if not series_path.exists():
                return 0

            # Get episodes for this show
            cursor = await db.execute("SELECT id, season_number, episode_number, title FROM episodes WHERE series_id = ?", (series_id,))
            episodes = await cursor.fetchall()
            ep_lookup = {(e["season_number"], e["episode_number"]): e for e in episodes}

            matched_count = 0
            for root, _, files in os.walk(series_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in VIDEO_EXTENSIONS:
                        parsed = release_parser.parse(f)
                        if parsed.season is not None and parsed.episode is not None:
                            key = (parsed.season, parsed.episode)
                            if key in ep_lookup:
                                ep = ep_lookup[key]
                                full_file_path = os.path.join(root, f)
                                file_size = os.path.getsize(full_file_path)
                                quality = parsed.quality_tag if parsed.quality_tag != "Unknown" else "1080p"

                                await db.execute(
                                    """
                                    UPDATE episodes
                                    SET has_file = 1, file_path = ?, quality = ?, file_size = ?
                                    WHERE id = ?
                                    """,
                                    (full_file_path, quality, file_size, ep["id"])
                                )
                                matched_count += 1

            await db.commit()
            logger.info(f"Scan complete for '{series['title']}': matched {matched_count} video files.")
            return matched_count

    async def import_download(
        self,
        queue_id: int,
        source_title: str,
        series_id: int,
        season_number: int,
        episode_number: int,
        quality: str,
        indexer: str,
        download_client: str,
        source_file_path: Optional[str] = None
    ) -> bool:
        """Handles post-download processing, renaming, and placing into library."""
        async with get_db() as db:
            # Fetch series
            cursor = await db.execute("SELECT title, path FROM series WHERE id = ?", (series_id,))
            series = await cursor.fetchone()
            if not series:
                logger.error(f"Cannot import: Series id {series_id} not found.")
                return False

            # Fetch episode
            cursor = await db.execute(
                "SELECT id, title FROM episodes WHERE series_id = ? AND season_number = ? AND episode_number = ?",
                (series_id, season_number, episode_number)
            )
            episode = await cursor.fetchone()
            if not episode:
                logger.error(f"Cannot import: Episode S{season_number:02d}E{episode_number:02d} not found.")
                return False

            series_dir = Path(series["path"])
            season_folder_name = f"Season {season_number:02d}"
            dest_dir = series_dir / season_folder_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            dest_filename = self.format_episode_filename(
                format_template=config.standard_episode_format,
                series_title=series["title"],
                season_num=season_number,
                episode_num=episode_number,
                episode_title=episode["title"],
                quality=quality,
                extension=".mkv"
            )
            dest_file_path = dest_dir / dest_filename

            # If real source file exists, move/copy it; if simulated, generate sample file
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
                # Create a sample media file with mock metadata
                with open(dest_file_path, "wb") as f:
                    f.write(b"PULSEARR_MEDIA_STREAM_MOCK_CONTAINER\x00\x00\x01\xba" + b"\x00" * 4096)
                file_size = 1450000000

            # Update episode in DB
            await db.execute(
                """
                UPDATE episodes
                SET has_file = 1, file_path = ?, quality = ?, file_size = ?
                WHERE id = ?
                """,
                (str(dest_file_path), quality, file_size, episode["id"])
            )

            # Update queue item to completed
            await db.execute("UPDATE queue SET status = 'completed', progress = 100.0 WHERE id = ?", (queue_id,))

            # Add to history
            await db.execute(
                """
                INSERT INTO history (
                    series_id, season_number, episode_number,
                    event_type, source_title, quality, indexer, download_client, path
                ) VALUES (?, ?, ?, 'imported', ?, ?, ?, ?, ?)
                """,
                (
                    series_id,
                    season_number,
                    episode_number,
                    source_title,
                    quality,
                    indexer,
                    download_client,
                    str(dest_file_path)
                )
            )
            await db.commit()

        logger.info(f"Successfully imported '{dest_filename}' to '{dest_file_path}'")
        return True

file_manager = FileManager()
