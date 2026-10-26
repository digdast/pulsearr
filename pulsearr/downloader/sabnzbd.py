import logging
import httpx
from typing import List, Dict, Any, Tuple
from .base import BaseDownloadClient

logger = logging.getLogger("pulsearr.downloader.sabnzbd")

class SABnzbdClient(BaseDownloadClient):
    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}/api"

    async def add(self, download_url: str, title: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "apikey": self.password,  # In SABnzbd, password field holds API key
                "mode": "addurl",
                "name": download_url,
                "nzbname": title,
                "cat": self.category or "tv",
                "output": "json"
            }
            resp = await client.get(self.api_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                nzo_ids = data.get("nzo_ids", [])
                return nzo_ids[0] if nzo_ids else "added"
            raise RuntimeError(f"SABnzbd add failed: {resp.status_code}")

    async def get_items(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                params = {
                    "apikey": self.password,
                    "mode": "queue",
                    "output": "json"
                }
                resp = await client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    return []
                queue = resp.json().get("queue", {})
                slots = queue.get("slots", [])
                results = []
                for s in slots:
                    total_mb = float(s.get("mb", 0))
                    left_mb = float(s.get("mbleft", 0))
                    done_mb = max(0, total_mb - left_mb)
                    pct = round((done_mb / total_mb * 100) if total_mb > 0 else 0, 1)
                    
                    results.append({
                        "id": s.get("nzo_id"),
                        "title": s.get("filename"),
                        "status": "downloading" if s.get("status") == "Downloading" else "queued",
                        "progress": pct,
                        "speed": int(float(queue.get("kbpersec", 0)) * 1024),
                        "eta": int(s.get("timeleft_sec", 0)),
                        "size": int(total_mb * 1024 * 1024)
                    })
                return results
        except Exception as e:
            logger.warning(f"Error fetching SABnzbd items: {e}")
            return []

    async def remove(self, client_item_id: str, delete_data: bool = False) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                params = {
                    "apikey": self.password,
                    "mode": "queue",
                    "name": "delete",
                    "value": client_item_id,
                    "del_files": 1 if delete_data else 0,
                    "output": "json"
                }
                resp = await client.get(self.api_url, params=params)
                return resp.status_code == 200
        except Exception:
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                params = {
                    "apikey": self.password,
                    "mode": "version",
                    "output": "json"
                }
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return True, f"Connected to SABnzbd v{data.get('version')} successfully."
                return False, f"HTTP error {resp.status_code}"
        except Exception as e:
            return False, f"SABnzbd connection failed: {str(e)}"
