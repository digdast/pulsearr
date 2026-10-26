import json
import logging
import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from .config import DB_PATH, DEFAULT_ROOT_FOLDER

logger = logging.getLogger("pulsearr.db")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tvmaze_id INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    sort_title TEXT NOT NULL,
    status TEXT NOT NULL,
    overview TEXT,
    poster_url TEXT,
    banner_url TEXT,
    network TEXT,
    genres TEXT,
    premiered TEXT,
    path TEXT NOT NULL,
    quality_profile_id INTEGER DEFAULT 1,
    monitored INTEGER DEFAULT 1,
    season_count INTEGER DEFAULT 0,
    episode_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    monitored INTEGER DEFAULT 1,
    episode_count INTEGER DEFAULT 0,
    FOREIGN KEY(series_id) REFERENCES series(id) ON DELETE CASCADE,
    UNIQUE(series_id, season_number)
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    tvmaze_id INTEGER UNIQUE NOT NULL,
    season_number INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    air_date TEXT,
    overview TEXT,
    monitored INTEGER DEFAULT 1,
    has_file INTEGER DEFAULT 0,
    file_path TEXT,
    quality TEXT,
    file_size INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(series_id) REFERENCES series(id) ON DELETE CASCADE,
    FOREIGN KEY(season_id) REFERENCES seasons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quality_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cutoff_id TEXT NOT NULL,
    items_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indexers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    api_key TEXT DEFAULT '',
    categories TEXT DEFAULT '5000,5030,5040',
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS download_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    host TEXT DEFAULT 'localhost',
    port INTEGER DEFAULT 8080,
    username TEXT DEFAULT '',
    password TEXT DEFAULT '',
    category TEXT DEFAULT 'tv',
    download_path TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    series_id INTEGER,
    season_number INTEGER,
    episode_number INTEGER,
    download_client_id INTEGER NOT NULL,
    client_item_id TEXT NOT NULL,
    protocol TEXT DEFAULT 'torrent',
    size INTEGER DEFAULT 0,
    status TEXT DEFAULT 'downloading',
    progress REAL DEFAULT 0.0,
    download_speed INTEGER DEFAULT 0,
    eta INTEGER DEFAULT 0,
    quality TEXT DEFAULT 'Unknown',
    indexer TEXT DEFAULT 'Unknown',
    download_url TEXT DEFAULT '',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(series_id) REFERENCES series(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER,
    season_number INTEGER,
    episode_number INTEGER,
    event_type TEXT NOT NULL,
    source_title TEXT NOT NULL,
    quality TEXT NOT NULL,
    indexer TEXT,
    download_client TEXT,
    path TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_json TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE,
    imdb_id TEXT UNIQUE,
    title TEXT NOT NULL,
    sort_title TEXT NOT NULL,
    year INTEGER NOT NULL,
    overview TEXT,
    poster_url TEXT,
    banner_url TEXT,
    genres TEXT,
    runtime INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.0,
    path TEXT NOT NULL,
    quality_profile_id INTEGER DEFAULT 1,
    monitored INTEGER DEFAULT 1,
    has_file INTEGER DEFAULT 0,
    file_path TEXT,
    quality TEXT,
    file_size INTEGER DEFAULT 0,
    release_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_id);
CREATE INDEX IF NOT EXISTS idx_episodes_air_date ON episodes(air_date);
CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);
CREATE INDEX IF NOT EXISTS idx_history_series ON history(series_id);
CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status);
"""

DEFAULT_QUALITY_PROFILES = [
    {
        "name": "HD - 1080p (Balanced)",
        "cutoff_id": "webdl-1080p",
        "items": [
            {"id": "bluray-1080p", "name": "BluRay-1080p", "score": 100, "resolution": "1080p", "source": "BluRay"},
            {"id": "webdl-1080p", "name": "WEB-DL 1080p", "score": 90, "resolution": "1080p", "source": "WEB-DL"},
            {"id": "webrip-1080p", "name": "WEBRip 1080p", "score": 80, "resolution": "1080p", "source": "WEBRip"},
            {"id": "hdtv-1080p", "name": "HDTV 1080p", "score": 70, "resolution": "1080p", "source": "HDTV"},
            {"id": "webdl-720p", "name": "WEB-DL 720p", "score": 60, "resolution": "720p", "source": "WEB-DL"},
            {"id": "hdtv-720p", "name": "HDTV 720p", "score": 50, "resolution": "720p", "source": "HDTV"}
        ]
    },
    {
        "name": "Ultra-HD - 4K (Cinematic)",
        "cutoff_id": "webdl-2160p",
        "items": [
            {"id": "remux-2160p", "name": "Remux-2160p", "score": 120, "resolution": "2160p", "source": "Remux"},
            {"id": "bluray-2160p", "name": "BluRay-2160p", "score": 110, "resolution": "2160p", "source": "BluRay"},
            {"id": "webdl-2160p", "name": "WEB-DL 2160p", "score": 100, "resolution": "2160p", "source": "WEB-DL"},
            {"id": "webrip-2160p", "name": "WEBRip 2160p", "score": 90, "resolution": "2160p", "source": "WEBRip"},
            {"id": "bluray-1080p", "name": "BluRay-1080p", "score": 75, "resolution": "1080p", "source": "BluRay"}
        ]
    },
    {
        "name": "Any Quality (Fastest)",
        "cutoff_id": "hdtv-720p",
        "items": [
            {"id": "bluray-1080p", "name": "BluRay-1080p", "score": 100, "resolution": "1080p", "source": "BluRay"},
            {"id": "webdl-1080p", "name": "WEB-DL 1080p", "score": 90, "resolution": "1080p", "source": "WEB-DL"},
            {"id": "webdl-720p", "name": "WEB-DL 720p", "score": 80, "resolution": "720p", "source": "WEB-DL"},
            {"id": "hdtv-720p", "name": "HDTV 720p", "score": 70, "resolution": "720p", "source": "HDTV"},
            {"id": "sd", "name": "SD / 480p", "score": 40, "resolution": "480p", "source": "SD"}
        ]
    }
]

DEFAULT_INDEXERS = [
    {
        "name": "EZTV Public Feed (TV Direct)",
        "type": "eztv",
        "url": "https://eztvx.to/api/get-torrents",
        "api_key": "",
        "categories": "5000",
        "enabled": 1,
        "priority": 1
    },
    {
        "name": "YTS Movie Public Feed (Movies Direct)",
        "type": "yts",
        "url": "https://yts.lt/api/v2",
        "api_key": "",
        "categories": "2000",
        "enabled": 1,
        "priority": 1
    },
    {
        "name": "Jackett / Prowlarr Torznab (TV & Movies)",
        "type": "torznab",
        "url": "http://localhost:9696/1/api",
        "api_key": "YOUR_API_KEY_HERE",
        "categories": "2000,5000,5030,5040",
        "enabled": 0,
        "priority": 2
    }
]

DEFAULT_DOWNLOAD_CLIENTS = [
    {
        "name": "Pulsearr Built-in Fast Simulator",
        "type": "simulator",
        "host": "localhost",
        "port": 0,
        "username": "",
        "password": "",
        "category": "tv",
        "download_path": "",
        "enabled": 1,
        "priority": 1
    },
    {
        "name": "qBittorrent (Local)",
        "type": "qbittorrent",
        "host": "localhost",
        "port": 8080,
        "username": "admin",
        "password": "adminadmin",
        "category": "tv",
        "download_path": "",
        "enabled": 0,
        "priority": 2
    },
    {
        "name": "Transmission (Local)",
        "type": "transmission",
        "host": "localhost",
        "port": 9091,
        "username": "",
        "password": "",
        "category": "tv",
        "download_path": "",
        "enabled": 0,
        "priority": 3
    },
    {
        "name": "SABnzbd (Usenet)",
        "type": "sabnzbd",
        "host": "localhost",
        "port": 8080,
        "username": "",
        "password": "YOUR_SABNZBD_API_KEY",
        "category": "tv",
        "download_path": "",
        "enabled": 0,
        "priority": 4
    }
]

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        await conn.execute("PRAGMA busy_timeout=30000;")
        yield conn

async def init_db():
    """Initializes the database schema and default seeds."""
    async with get_db() as db:
        await db.executescript(SCHEMA_SQL)
        
        # Check if quality profiles exist
        cursor = await db.execute("SELECT COUNT(*) FROM quality_profiles")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for p in DEFAULT_QUALITY_PROFILES:
                await db.execute(
                    "INSERT INTO quality_profiles (name, cutoff_id, items_json) VALUES (?, ?, ?)",
                    (p["name"], p["cutoff_id"], json.dumps(p["items"]))
                )
        
        # Check indexers
        cursor = await db.execute("SELECT COUNT(*) FROM indexers")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for idx in DEFAULT_INDEXERS:
                await db.execute(
                    "INSERT INTO indexers (name, type, url, api_key, categories, enabled, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (idx["name"], idx["type"], idx["url"], idx["api_key"], idx["categories"], idx["enabled"], idx["priority"])
                )
        
        # Check download clients
        cursor = await db.execute("SELECT COUNT(*) FROM download_clients")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for dc in DEFAULT_DOWNLOAD_CLIENTS:
                await db.execute(
                    "INSERT INTO download_clients (name, type, host, port, username, password, category, download_path, enabled, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (dc["name"], dc["type"], dc["host"], dc["port"], dc["username"], dc["password"], dc["category"], dc["download_path"], dc["enabled"], dc["priority"])
                )
                
        # Run column migrations for existing databases
        migrations = [
            "ALTER TABLE indexers ADD COLUMN capabilities TEXT DEFAULT 'both'",
            "ALTER TABLE indexers ADD COLUMN latency_ms INTEGER DEFAULT 0",
            "ALTER TABLE indexers ADD COLUMN last_checked TIMESTAMP",
            "ALTER TABLE download_clients ADD COLUMN use_ssl INTEGER DEFAULT 0",
            "ALTER TABLE download_clients ADD COLUMN url_base TEXT DEFAULT ''",
            "ALTER TABLE download_clients ADD COLUMN media_type TEXT DEFAULT 'both'",
            "ALTER TABLE download_clients ADD COLUMN remote_path TEXT DEFAULT ''",
            "ALTER TABLE download_clients ADD COLUMN local_path TEXT DEFAULT ''",
            "ALTER TABLE queue ADD COLUMN media_type TEXT DEFAULT 'tv'",
            "ALTER TABLE queue ADD COLUMN movie_id INTEGER REFERENCES movies(id) ON DELETE SET NULL",
            "ALTER TABLE history ADD COLUMN media_type TEXT DEFAULT 'tv'",
            "ALTER TABLE history ADD COLUMN movie_id INTEGER"
        ]
        for m in migrations:
            try:
                await db.execute(m)
            except Exception:
                pass  # Column already exists

        # Check and add YTS indexer if missing
        cursor = await db.execute("SELECT COUNT(*) FROM indexers WHERE type = 'yts'")
        if (await cursor.fetchone())[0] == 0:
            await db.execute(
                "INSERT INTO indexers (name, type, url, api_key, categories, enabled, priority, capabilities) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("YTS Movie Public Feed (Movies Direct)", "yts", "https://yts.lt/api/v2", "", "2000", 1, 1, "movie")
            )

        # Default settings
        movie_root = str(Path(DEFAULT_ROOT_FOLDER).parent / "movies")
        default_settings = {
            "root_folder": DEFAULT_ROOT_FOLDER,
            "movies_root_folder": movie_root,
            "standard_episode_format": "{Series Title} - S{season:02d}E{episode:02d} - {Episode Title} [{Quality}]",
            "standard_movie_format": "{Movie Title} ({Year}) [{Quality}]",
            "import_mode": "move",
            "auto_import": "true",
            "rename_episodes": "true"
        }
        for k, v in default_settings.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
            
        await db.commit()
        logger.info("Database initialized successfully with WAL mode.")
