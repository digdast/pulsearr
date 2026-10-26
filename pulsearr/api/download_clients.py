import logging
from typing import List
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models import DownloadClientConfig
from ..downloader.manager import download_manager

logger = logging.getLogger("pulsearr.api.download_clients")
router = APIRouter(prefix="/download-clients", tags=["Download Clients"])

@router.get("", response_model=List[DownloadClientConfig])
async def list_download_clients():
    """Lists configured download clients including remote seedbox configurations."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM download_clients ORDER BY priority ASC")
        rows = await cursor.fetchall()
        return [
            DownloadClientConfig(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                host=r["host"],
                port=r["port"],
                use_ssl=bool(r["use_ssl"]) if "use_ssl" in r.keys() else False,
                url_base=r["url_base"] if "url_base" in r.keys() and r["url_base"] else "",
                username=r["username"] or "",
                password=r["password"] or "",
                category=r["category"] or "tv",
                media_type=r["media_type"] if "media_type" in r.keys() and r["media_type"] else "both",
                download_path=r["download_path"] or "",
                remote_path=r["remote_path"] if "remote_path" in r.keys() and r["remote_path"] else "",
                local_path=r["local_path"] if "local_path" in r.keys() and r["local_path"] else "",
                enabled=bool(r["enabled"]),
                priority=r["priority"]
            )
            for r in rows
        ]

@router.post("", response_model=dict)
async def create_download_client(payload: DownloadClientConfig):
    """Creates a new download client configuration with remote host and path mapping support."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO download_clients (
                name, type, host, port, use_ssl, url_base, username, password,
                category, media_type, download_path, remote_path, local_path, enabled, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name, payload.type, payload.host, payload.port,
                1 if payload.use_ssl else 0, payload.url_base or "",
                payload.username, payload.password, payload.category,
                payload.media_type, payload.download_path,
                payload.remote_path or "", payload.local_path or "",
                1 if payload.enabled else 0, payload.priority
            )
        )
        await db.commit()
        return {"id": cursor.lastrowid, "status": "created"}

@router.put("/{client_id}")
async def update_download_client(client_id: int, payload: DownloadClientConfig):
    """Updates an existing download client configuration."""
    async with get_db() as db:
        await db.execute(
            """
            UPDATE download_clients
            SET name = ?, type = ?, host = ?, port = ?, use_ssl = ?, url_base = ?,
                username = ?, password = ?, category = ?, media_type = ?,
                download_path = ?, remote_path = ?, local_path = ?, enabled = ?, priority = ?
            WHERE id = ?
            """,
            (
                payload.name, payload.type, payload.host, payload.port,
                1 if payload.use_ssl else 0, payload.url_base or "",
                payload.username, payload.password, payload.category,
                payload.media_type, payload.download_path,
                payload.remote_path or "", payload.local_path or "",
                1 if payload.enabled else 0, payload.priority, client_id
            )
        )
        await db.commit()
    return {"status": "updated"}

@router.delete("/{client_id}")
async def delete_download_client(client_id: int):
    """Deletes a download client configuration."""
    async with get_db() as db:
        await db.execute("DELETE FROM download_clients WHERE id = ?", (client_id,))
        await db.commit()
    return {"status": "deleted"}

@router.post("/{client_id}/test")
async def test_download_client(client_id: int):
    """Tests connection to a download client."""
    client = await download_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Download client not found")

    success, msg = await client.test_connection()
    return {"success": success, "message": msg}
