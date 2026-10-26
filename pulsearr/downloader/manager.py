import logging
from typing import List, Optional, Tuple, Dict, Any
from .base import BaseDownloadClient
from .qbittorrent import QBittorrentClient
from .transmission import TransmissionClient
from .sabnzbd import SABnzbdClient
from .simulator import SimulatorClient
from ..database import get_db
from ..models import ReleaseCandidate

logger = logging.getLogger("pulsearr.downloader.manager")

class DownloadClientManager:
    async def get_client(self, client_id: Optional[int] = None, media_type: str = "both") -> Optional[BaseDownloadClient]:
        """Fetches client by ID or returns highest priority enabled client matching media_type."""
        async with get_db() as db:
            if client_id:
                cursor = await db.execute("SELECT * FROM download_clients WHERE id = ?", (client_id,))
            else:
                # Query clients supporting media_type or 'both'
                cursor = await db.execute(
                    """
                    SELECT * FROM download_clients 
                    WHERE enabled = 1 AND (media_type = 'both' OR media_type = ? OR media_type IS NULL)
                    ORDER BY priority ASC LIMIT 1
                    """,
                    (media_type,)
                )
            row = await cursor.fetchone()
            if not row:
                return None

            ctype = row["type"].lower()
            kwargs = {
                "id": row["id"],
                "name": row["name"],
                "host": row["host"],
                "port": row["port"],
                "username": row["username"] or "",
                "password": row["password"] or "",
                "category": row["category"] or ("movies" if media_type == "movie" else "tv"),
                "download_path": row["download_path"] or "",
                "use_ssl": bool(row["use_ssl"]) if "use_ssl" in row.keys() else False,
                "url_base": row["url_base"] if "url_base" in row.keys() else "",
                "remote_path": row["remote_path"] if "remote_path" in row.keys() else "",
                "local_path": row["local_path"] if "local_path" in row.keys() else "",
                "media_type": row["media_type"] if "media_type" in row.keys() else "both"
            }

            if ctype == "simulator":
                return SimulatorClient(**kwargs)
            elif ctype == "qbittorrent":
                return QBittorrentClient(**kwargs)
            elif ctype == "transmission":
                return TransmissionClient(**kwargs)
            elif ctype == "sabnzbd":
                return SABnzbdClient(**kwargs)
            return None

    async def grab_release(
        self,
        candidate: ReleaseCandidate,
        media_type: str = "tv",
        series_id: Optional[int] = None,
        movie_id: Optional[int] = None,
        season_number: Optional[int] = None,
        episode_number: Optional[int] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Dispatches release candidate to download client and logs in database."""
        client = await self.get_client(client_id, media_type=media_type)
        if not client:
            raise RuntimeError("No active download client configured for this media type.")

        # Add to download client
        client_item_id = await client.add(candidate.download_url, candidate.title)

        # Record in queue
        async with get_db() as db:
            cursor = await db.execute(
                """
                INSERT INTO queue (
                    title, media_type, series_id, movie_id, season_number, episode_number,
                    download_client_id, client_item_id, protocol, size,
                    status, progress, download_speed, eta, quality, indexer, download_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'downloading', 0.0, 0, 0, ?, ?, ?)
                """,
                (
                    candidate.title,
                    media_type,
                    series_id,
                    movie_id,
                    season_number or candidate.parsed.season,
                    episode_number or candidate.parsed.episode,
                    client.id,
                    client_item_id,
                    candidate.protocol,
                    candidate.size,
                    candidate.parsed.quality_tag,
                    candidate.indexer_name,
                    candidate.download_url
                )
            )
            queue_id = cursor.lastrowid

            # Record in history
            await db.execute(
                """
                INSERT INTO history (
                    media_type, series_id, movie_id, season_number, episode_number,
                    event_type, source_title, quality, indexer, download_client
                ) VALUES (?, ?, ?, ?, ?, 'grabbed', ?, ?, ?, ?)
                """,
                (
                    media_type,
                    series_id,
                    movie_id,
                    season_number or candidate.parsed.season,
                    episode_number or candidate.parsed.episode,
                    candidate.title,
                    candidate.parsed.quality_tag,
                    candidate.indexer_name,
                    client.name
                )
            )
            await db.commit()

        logger.info(f"Grabbed {media_type} release '{candidate.title}' via {client.name} (queue_id={queue_id})")
        return {"queue_id": queue_id, "client_item_id": client_item_id, "client_name": client.name}

download_manager = DownloadClientManager()
