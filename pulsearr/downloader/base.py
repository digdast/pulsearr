import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional

class BaseDownloadClient(ABC):
    def __init__(
        self,
        id: int,
        name: str,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        category: str = "tv",
        download_path: str = "",
        use_ssl: bool = False,
        url_base: str = "",
        remote_path: str = "",
        local_path: str = "",
        media_type: str = "both",
        **kwargs
    ):
        self.id = id
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.category = category
        self.download_path = download_path
        self.use_ssl = use_ssl
        self.url_base = url_base or ""
        self.remote_path = remote_path or ""
        self.local_path = local_path or ""
        self.media_type = media_type or "both"

    def map_remote_path(self, path: Optional[str]) -> Optional[str]:
        """Translates a remote seedbox/host filesystem path into a local filesystem path."""
        if not path:
            return path
        if self.remote_path and self.local_path:
            clean_remote = self.remote_path.rstrip("/\\")
            clean_local = self.local_path.rstrip("/\\")
            if path.startswith(clean_remote):
                rel = path[len(clean_remote):].lstrip("/\\")
                return os.path.join(clean_local, rel.replace("/", os.sep).replace("\\", os.sep))
        return path

    @abstractmethod
    async def add(self, download_url: str, title: str) -> str:
        """Adds release to client. Returns client item ID / hash."""
        pass

    @abstractmethod
    async def get_items(self) -> List[Dict[str, Any]]:
        """Returns list of active items: id, status, progress (0-100), speed (B/s), eta (s), size."""
        pass

    @abstractmethod
    async def remove(self, client_item_id: str, delete_data: bool = False) -> bool:
        """Removes release from client."""
        pass

    @abstractmethod
    async def test_connection(self) -> Tuple[bool, str]:
        """Tests connection to client."""
        pass
