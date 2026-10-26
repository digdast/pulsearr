from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class QualityItem(BaseModel):
    id: str
    name: str
    score: int
    resolution: str
    source: str
    min_size_mb: Optional[int] = 0
    max_size_mb: Optional[int] = None

class QualityProfile(BaseModel):
    id: int
    name: str
    cutoff_id: str
    items: List[QualityItem] = []

class SeriesCreate(BaseModel):
    tvmaze_id: int
    title: str
    path: Optional[str] = None
    quality_profile_id: int = 1
    monitored: bool = True
    season_folder: bool = True

class SeriesUpdate(BaseModel):
    monitored: Optional[bool] = None
    quality_profile_id: Optional[int] = None
    path: Optional[str] = None
    season_folder: Optional[bool] = None

class EpisodeModel(BaseModel):
    id: int
    series_id: int
    season_id: int
    tvmaze_id: int
    season_number: int
    episode_number: int
    title: str
    air_date: Optional[str] = None
    overview: Optional[str] = None
    monitored: bool = True
    has_file: bool = False
    file_path: Optional[str] = None
    quality: Optional[str] = None
    file_size: Optional[int] = 0

class SeasonModel(BaseModel):
    id: int
    series_id: int
    season_number: int
    monitored: bool = True
    episode_count: int = 0
    episodes: List[EpisodeModel] = []

class SeriesModel(BaseModel):
    id: int
    tvmaze_id: int
    title: str
    sort_title: str
    status: str
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    banner_url: Optional[str] = None
    network: Optional[str] = None
    genres: List[str] = []
    premiered: Optional[str] = None
    path: str
    quality_profile_id: int = 1
    monitored: bool = True
    season_count: int = 0
    episode_count: int = 0
    downloaded_episode_count: int = 0
    created_at: str
    updated_at: str

class ParsedRelease(BaseModel):
    title: str
    clean_title: str
    season: Optional[int] = None
    episode: Optional[int] = None
    season_pack: bool = False
    resolution: str = "Unknown"
    source: str = "Unknown"
    codec: str = "Unknown"
    audio: str = "Unknown"
    hdr: str = "SDR"
    release_group: str = "Unknown"
    proper: bool = False
    repack: bool = False
    quality_tag: str = "Unknown"
    score: int = 0

class ReleaseCandidate(BaseModel):
    guid: str
    indexer_id: int
    indexer_name: str
    title: str
    download_url: str
    info_url: Optional[str] = None
    protocol: str = "torrent"  # torrent or usenet
    size: int = 0
    publish_date: Optional[str] = None
    seeders: Optional[int] = 0
    leechers: Optional[int] = 0
    parsed: ParsedRelease
    meets_cutoff: bool = True
    reject_reasons: List[str] = []

class MovieModel(BaseModel):
    id: int
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    title: str
    sort_title: str
    year: int
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    banner_url: Optional[str] = None
    genres: List[str] = []
    runtime: int = 0
    rating: float = 0.0
    path: str
    quality_profile_id: int = 1
    monitored: bool = True
    has_file: bool = False
    file_path: Optional[str] = None
    quality: Optional[str] = None
    file_size: int = 0
    release_date: Optional[str] = None
    created_at: str
    updated_at: str

class MovieCreate(BaseModel):
    title: str
    year: int
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    rating: Optional[float] = 0.0
    runtime: Optional[int] = 0
    genres: List[str] = []
    path: Optional[str] = None
    quality_profile_id: int = 1
    monitored: bool = True

class MovieUpdate(BaseModel):
    monitored: Optional[bool] = None
    quality_profile_id: Optional[int] = None
    path: Optional[str] = None

class QueueItemModel(BaseModel):
    id: int
    title: str
    media_type: str = "tv"  # tv or movie
    series_id: Optional[int] = None
    movie_id: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    download_client_id: int
    client_item_id: str
    protocol: str
    size: int
    status: str  # downloading, completed, paused, queued, importing, failed
    progress: float
    download_speed: int
    eta: int
    quality: str
    indexer: str
    download_url: str
    added_at: str
    series_title: Optional[str] = None
    movie_title: Optional[str] = None

class IndexerConfig(BaseModel):
    id: Optional[int] = None
    name: str
    type: str  # torznab, newznab, rss, eztv, yts
    url: str
    api_key: Optional[str] = ""
    categories: str = "2000,5000,5030,5040"
    capabilities: str = "both"  # tv, movie, both
    enabled: bool = True
    priority: int = 1
    latency_ms: Optional[int] = 0

class DownloadClientConfig(BaseModel):
    id: Optional[int] = None
    name: str
    type: str  # qbittorrent, transmission, sabnzbd, blackhole, simulator
    host: str = "localhost"
    port: int = 8080
    use_ssl: bool = False
    url_base: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    category: str = "tv"
    media_type: str = "both"  # tv, movie, both
    download_path: Optional[str] = ""
    # Remote Path Mapping for Seedboxes
    remote_path: Optional[str] = ""
    local_path: Optional[str] = ""
    enabled: bool = True
    priority: int = 1

class HistoryItemModel(BaseModel):
    id: int
    media_type: str = "tv"  # tv or movie
    series_id: Optional[int] = None
    movie_id: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    event_type: str  # grabbed, imported, deleted, failed
    source_title: str
    quality: str
    indexer: Optional[str] = None
    download_client: Optional[str] = None
    path: Optional[str] = None
    timestamp: str
    series_title: Optional[str] = None
    movie_title: Optional[str] = None

