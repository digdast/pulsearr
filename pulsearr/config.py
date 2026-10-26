import os
import secrets
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory Resolution
PULSEARR_DIR = Path(__file__).resolve().parent.parent
data_env = os.getenv("PULSEARR_DATA_DIR")
DATA_DIR = Path(data_env) if data_env else (PULSEARR_DIR / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "pulsearr.db"
DEFAULT_ROOT_FOLDER = str(DATA_DIR / "media" / "tv")
os.makedirs(DEFAULT_ROOT_FOLDER, exist_ok=True)

class AppConfig(BaseModel):
    app_name: str = "Pulsearr"
    version: str = "1.0.0"
    host: str = os.getenv("PULSEARR_HOST", "0.0.0.0")
    port: int = int(os.getenv("PULSEARR_PORT", "8990"))  # Default 8990
    api_key: str = Field(default_factory=lambda: secrets.token_hex(16))
    debug: bool = False
    
    # Naming Format
    # Tokens: {Series Title}, {season:02d}, {episode:02d}, {Episode Title}, {Quality}
    standard_episode_format: str = "{Series Title} - S{season:02d}E{episode:02d} - {Episode Title} [{Quality}]"
    series_folder_format: str = "{Series Title}"
    season_folder_format: str = "Season {season:02d}"
    
    # Scheduling
    rss_sync_interval_minutes: int = 15
    queue_poll_interval_seconds: int = 5
    disk_scan_interval_minutes: int = 60
    
    # Organization
    import_mode: str = "move"  # 'copy', 'move', 'hardlink', 'symlink'
    auto_import: bool = True
    rename_episodes: bool = True
    delete_empty_folders: bool = True
    
    # Default Paths
    root_folder: str = DEFAULT_ROOT_FOLDER

config = AppConfig()
