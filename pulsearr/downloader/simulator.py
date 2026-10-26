import time
import uuid
from typing import List, Dict, Any, Tuple
from .base import BaseDownloadClient

class SimulatorClient(BaseDownloadClient):
    """Built-in virtual download client that simulates high-speed downloads

    and triggers instant completion for immediate out-of-the-box operation and testing.
    """
    _simulated_items: Dict[str, Dict[str, Any]] = {}

    async def add(self, download_url: str, title: str) -> str:
        item_id = f"sim-{uuid.uuid4().hex[:8]}"
        self._simulated_items[item_id] = {
            "id": item_id,
            "title": title,
            "start_time": time.time(),
            "duration": 6,  # 6 seconds to complete full download simulation
            "size": 1450000000, # 1.45 GB
            "speed": 28500000,   # ~28.5 MB/s
            "status": "downloading"
        }
        return item_id

    async def get_items(self) -> List[Dict[str, Any]]:
        now = time.time()
        results = []
        for item_id, item in list(self._simulated_items.items()):
            elapsed = now - item["start_time"]
            pct = min(100.0, round((elapsed / item["duration"]) * 100, 1))
            status = "completed" if pct >= 100.0 else "downloading"
            item["status"] = status
            eta = max(0, int(item["duration"] - elapsed)) if status == "downloading" else 0
            speed = item["speed"] if status == "downloading" else 0

            results.append({
                "id": item_id,
                "title": item["title"],
                "status": status,
                "progress": pct,
                "speed": speed,
                "eta": eta,
                "size": item["size"]
            })
        return results

    async def remove(self, client_item_id: str, delete_data: bool = False) -> bool:
        if client_item_id in self._simulated_items:
            del self._simulated_items[client_item_id]
            return True
        return False

    async def test_connection(self) -> Tuple[bool, str]:
        return True, "Pulsearr Built-in Virtual Downloader is active and ready."
