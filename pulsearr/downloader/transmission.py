import logging
import httpx
from typing import List, Dict, Any, Tuple, Optional
from .base import BaseDownloadClient

logger = logging.getLogger("pulsearr.downloader.transmission")

class TransmissionClient(BaseDownloadClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_id: Optional[str] = None

    @property
    def rpc_url(self) -> str:
        return f"http://{self.host}:{self.port}/transmission/rpc"

    async def _rpc_call(self, method: str, arguments: dict) -> dict:
        headers = {}
        if self._session_id:
            headers["X-Transmission-Session-Id"] = self._session_id
            
        auth = (self.username, self.password) if self.username else None
        async with httpx.AsyncClient(timeout=10.0, auth=auth) as client:
            resp = await client.post(self.rpc_url, json={"method": method, "arguments": arguments}, headers=headers)
            if resp.status_code == 409:
                self._session_id = resp.headers.get("X-Transmission-Session-Id")
                headers["X-Transmission-Session-Id"] = self._session_id
                resp = await client.post(self.rpc_url, json={"method": method, "arguments": arguments}, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("arguments", {})
            raise RuntimeError(f"Transmission RPC error {resp.status_code}: {resp.text}")

    async def add(self, download_url: str, title: str) -> str:
        args = {"filename": download_url}
        if self.download_path:
            args["download-dir"] = self.download_path
        res = await self._rpc_call("torrent-add", args)
        torrent_added = res.get("torrent-added") or res.get("torrent-duplicate") or {}
        return str(torrent_added.get("hashString") or torrent_added.get("id"))

    async def get_items(self) -> List[Dict[str, Any]]:
        try:
            res = await self._rpc_call("torrent-get", {"fields": ["id", "hashString", "name", "status", "percentDone", "rateDownload", "eta", "totalSize"]})
            torrents = res.get("torrents", [])
            results = []
            for t in torrents:
                # Transmission status: 4=download, 6=seed
                status = "downloading"
                if t.get("status") in (5, 6):
                    status = "completed"
                elif t.get("status") == 0:
                    status = "paused"
                    
                results.append({
                    "id": str(t.get("hashString") or t.get("id")),
                    "title": t.get("name"),
                    "status": status,
                    "progress": round(float(t.get("percentDone", 0.0)) * 100, 1),
                    "speed": int(t.get("rateDownload", 0)),
                    "eta": int(t.get("eta", 0)),
                    "size": int(t.get("totalSize", 0))
                })
            return results
        except Exception as e:
            logger.warning(f"Failed to fetch Transmission torrents: {e}")
            return []

    async def remove(self, client_item_id: str, delete_data: bool = False) -> bool:
        try:
            await self._rpc_call("torrent-remove", {"ids": [client_item_id], "delete-local-data": delete_data})
            return True
        except Exception:
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        try:
            res = await self._rpc_call("session-get", {})
            version = res.get("version", "unknown")
            return True, f"Connected to Transmission v{version} successfully."
        except Exception as e:
            return False, f"Transmission connection failed: {str(e)}"
