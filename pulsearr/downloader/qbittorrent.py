import logging
import httpx
from typing import List, Dict, Any, Tuple, Optional
from .base import BaseDownloadClient

logger = logging.getLogger("pulsearr.downloader.qbittorrent")

class QBittorrentClient(BaseDownloadClient):
    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_ssl else "http"
        clean_host = self.host.replace("http://", "").replace("https://", "").rstrip('/')
        port_suffix = f":{self.port}" if self.port not in (80, 443, 0) else ""
        subpath = f"/{self.url_base.strip('/')}" if self.url_base and self.url_base.strip('/') else ""
        return f"{protocol}://{clean_host}{port_suffix}{subpath}"

    async def _get_auth_cookie(self) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v2/auth/login",
                    data={"username": self.username, "password": self.password}
                )
                if resp.status_code == 200 and resp.text.strip() == "Ok.":
                    return dict(resp.cookies)
        except Exception as e:
            logger.warning(f"qBittorrent login failed ({self.base_url}): {e}")
        return None

    async def add(self, download_url: str, title: str) -> str:
        cookies = await self._get_auth_cookie()
        async with httpx.AsyncClient(timeout=12.0, cookies=cookies, verify=False) as client:
            data = {
                "urls": download_url,
                "category": self.category
            }
            if self.download_path:
                data["savepath"] = self.download_path
            resp = await client.post(f"{self.base_url}/api/v2/torrents/add", data=data)
            if resp.status_code == 200:
                return "added"
            raise RuntimeError(f"qBittorrent add failed: {resp.status_code} {resp.text}")

    async def get_items(self) -> List[Dict[str, Any]]:
        cookies = await self._get_auth_cookie()
        try:
            async with httpx.AsyncClient(timeout=8.0, cookies=cookies, verify=False) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v2/torrents/info",
                    params={"category": self.category} if self.category else {}
                )
                if resp.status_code != 200:
                    return []
                torrents = resp.json()
                results = []
                for t in torrents:
                    state = t.get("state", "").lower()
                    status = "downloading"
                    if "upload" in state or "complete" in state or state == "pausedup":
                        status = "completed"
                    elif "pause" in state:
                        status = "paused"
                    elif "error" in state:
                        status = "failed"
                    elif "queued" in state:
                        status = "queued"

                    raw_path = t.get("content_path") or t.get("save_path")
                    # Map remote seedbox path to local host path if configured
                    local_mapped_path = self.map_remote_path(raw_path)

                    results.append({
                        "id": t.get("hash"),
                        "title": t.get("name"),
                        "status": status,
                        "progress": round(float(t.get("progress", 0.0)) * 100, 1),
                        "speed": int(t.get("dlspeed", 0)),
                        "eta": int(t.get("eta", 0)),
                        "size": int(t.get("total_size", 0)),
                        "save_path": local_mapped_path,
                        "remote_save_path": raw_path
                    })
                return results
        except Exception as e:
            logger.warning(f"Error querying qBittorrent: {e}")
            return []

    async def remove(self, client_item_id: str, delete_data: bool = False) -> bool:
        cookies = await self._get_auth_cookie()
        async with httpx.AsyncClient(timeout=8.0, cookies=cookies, verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/torrents/delete",
                data={"hashes": client_item_id, "deleteFiles": "true" if delete_data else "false"}
            )
            return resp.status_code == 200

    async def test_connection(self) -> Tuple[bool, str]:
        try:
            cookies = await self._get_auth_cookie()
            if not cookies:
                return False, f"Authentication failed with qBittorrent at {self.base_url}."
            async with httpx.AsyncClient(timeout=8.0, cookies=cookies, verify=False) as client:
                resp = await client.get(f"{self.base_url}/api/v2/app/version")
                if resp.status_code == 200:
                    return True, f"Connected to qBittorrent v{resp.text.strip()} ({self.base_url})."
                return False, f"Connected but API returned HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Connection failed to {self.base_url}: {str(e)}"
