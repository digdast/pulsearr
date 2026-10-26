# ⚡ Pulsearr

> **Next-Gen Asynchronous Python TV PVR — Lighter, Smarter, and Faster than Sonarr.**

Pulsearr is a modern, high-performance automated TV series manager and PVR designed in pure async Python (`Python 3.11+ / 3.14`). It replaces heavy .NET dependencies with asynchronous I/O, SQLite WAL concurrent mode, a fast regex release parser, TVMaze zero-latency metadata search, and an Obsidian Glassmorphism single-page UI.

---

## 🚀 Why Pulsearr is Better & Faster than Sonarr

| Feature / Metric | Sonarr (.NET / C#) | Pulsearr (Modern Python) |
| :--- | :--- | :--- |
| **Startup Time** | 10 – 25 seconds | **~250 milliseconds** |
| **RAM Footprint** | ~350 MB – 800 MB | **~35 MB – 50 MB** |
| **Metadata Source** | Skyhook proxy (prone to timeouts / API keys) | **Direct TVMaze API (Instant typeahead, 0 keys needed)** |
| **Database Engine** | SQLite (common database lock errors) | **SQLite with WAL Mode + 30s busy timeout** |
| **Release Parser** | Hundreds of C# parser classes | **Fast compiled regex release parser (< 1ms per release)** |
| **Download Clients** | External clients only | **Built-in Fast Simulator + qBittorrent, Transmission, SABnzbd** |
| **Frontend UI** | Heavy React bundle (~10MB+) | **Ultra-lightweight Vanilla JS + CSS Glassmorphism (< 100KB)** |
| **Real-Time Updates** | Periodic HTTP polling | **Native Server-Sent Events (SSE) Stream** |
| **API** | REST API | **FastAPI with auto-generated OpenAPI /docs** |

---

## ✨ Core Features

1. **TV Series & Episode Management (Sonarr)**:
   - Live typeahead TV search powered by TVMaze (covers all shows, seasons, episodes, synopsis, high-res posters, banners, and air dates).
   - Monitored status flags per show, season, or episode.
   - Automatic library directory creation and organization.

2. **Movie Library & Management (Radarr)**:
   - Built directly into the same suite — no need for separate ports or extra apps!
   - Instant movie search with synopsis, release year, runtime, ratings, genres, and high-res cover art.
   - Direct movie release indexing via YTS public feed and Torznab/Newznab indexers.
   - Dedicated movie renaming tokens: `{Movie Title} ({Year}) [{Quality}].mkv`.

3. **Trackers & Indexer Hub (Prowlarr)**:
   - Unified indexer management supporting Torznab, Newznab, EZTV, and YTS.
   - Concurrent tracker latency benchmarking with visual color-coded speed pills.
   - Automatic category and media-type routing (TV, Movies, or Both).

4. **Remote qBittorrent & Seedbox Integration**:
   - Supports both local and remote qBittorrent hosts.
   - Secure HTTPS/SSL connections with custom URL base paths (e.g. `/qbittorrent`).
   - Remote-to-Local path mapping (e.g. `/home/user/downloads` ➔ `Z:\seedbox_mount` or `/mnt/seedbox`) for automatic importing across networked drives and SSHFS mounts.
   - Selective media routing: dedicate clients to TV, Movies, or Both.

5. **Multi-Client Downloader Engine**:
   - **Pulsearr Built-in Fast Simulator**: Runs an in-process download simulation (28.5 MB/s) and triggers auto-import for immediate demonstration, testing, and zero-setup usage.
   - **qBittorrent**: Web API v2 with SSL and path translation.
   - **Transmission**: RPC JSON integration with download-dir routing.
   - **SABnzbd**: Usenet API integration for `.nzb` release queues.

6. **Automated Media Organizer & Renamer**:
   - Live token-based renaming engine for TV and Movies.
   - Real-time naming pattern previewer directly in the UI settings.
   - Import modes: `move`, `copy`, or `hardlink` (allowing continued seeding with zero storage penalty).

7. **Automated Scheduler**:
   - Periodic background RSS sync across all active indexers.
   - Real-time queue monitor (polls every 5 seconds).
   - Auto-import trigger as soon as downloads hit 100%.

---

## 🛠️ Quick Start & Installation

### Windows Installation

Double click [`pulsearr.bat`](file:///c:/scripts/pulsearr/pulsearr.bat) or run:

```bash
cd c:\scripts\pulsearr
python run.py
```

---

### 🐧 Debian / Ubuntu / Linux Mint / Raspberry Pi Installation

Pulsearr includes a fully automated 1-click installer for any Debian-based machine:

```bash
# 1. Transfer or clone Pulsearr to your Linux server
# 2. Run the automated installer with root privileges:
sudo bash install.sh
```

**What the installer does automatically:**
1. Installs required system packages (`python3`, `python3-venv`, `python3-pip`, `sqlite3`, `curl`).
2. Creates an isolated, dedicated system service user `pulsearr`.
3. Deploys the application to `/opt/pulsearr`.
4. Creates a dedicated Python virtual environment and installs all dependencies.
5. Configures and registers a **`systemd`** service (`pulsearr.service`) that automatically starts on system boot.
6. Installs the handy `/usr/local/bin/pulsearr` CLI helper command.

**Managing the service on Debian/Ubuntu:**
```bash
pulsearr status      # Check service status
pulsearr logs        # Follow real-time live logs
pulsearr restart     # Restart service
pulsearr stop        # Stop service
pulsearr start       # Start service
```

---

### 🐳 Docker & Docker Compose (Any Linux Host)

If you prefer running Pulsearr inside a Docker container on Debian:

```bash
docker compose up -d --build
```

---

### Accessing the Dashboard

- **Web Dashboard**: `http://<your-server-ip>:8990` (or `http://localhost:8990`)
- **Interactive OpenAPI Docs**: `http://<your-server-ip>:8990/docs`

---

## 📁 Directory Structure

```text
c:\scripts\pulsearr\
├── pulsearr\
│   ├── config.py              # Configuration & defaults
│   ├── database.py            # Async SQLite with WAL mode & schemas
│   ├── models.py              # Pydantic data schemas (TV, Movies, Clients, Trackers)
│   ├── main.py                # FastAPI app lifecycle
│   ├── metadata\
│   │   ├── tvmaze.py          # Fast TVMaze metadata client
│   │   └── movies.py          # Public movie metadata client
│   ├── parser\
│   │   └── release_parser.py  # Regex release parser & scoring
│   ├── indexers\
│   │   ├── base.py            # Base indexer interface
│   │   ├── torznab.py         # Torznab & Newznab XML/JSON client
│   │   ├── eztv.py            # Direct EZTV API indexer
│   │   ├── yts.py             # Direct YTS Movies API indexer
│   │   └── manager.py         # Parallel search & score engine
│   ├── downloader\
│   │   ├── base.py            # Base download client
│   │   ├── simulator.py       # Built-in Virtual Downloader
│   │   ├── qbittorrent.py     # Remote & Local qBittorrent Web API v2
│   │   ├── transmission.py    # Transmission RPC client
│   │   ├── sabnzbd.py         # SABnzbd Usenet client
│   │   └── manager.py         # Client dispatcher & queue logger
│   ├── organizer\
│   │   ├── file_manager.py    # TV scanner, renamer, and importer
│   │   └── movie_manager.py   # Movie scanner, renamer, and importer
│   ├── scheduler\
│   │   └── engine.py          # RSS sync, queue poll, and SSE stream
│   └── api\                   # Modular REST API routers (series, movies, trackers, etc.)
├── static\
│   ├── css\style.css          # Obsidian Glassmorphism Design System
│   └── js\app.js              # Reactive Vanilla JavaScript SPA engine
├── templates\
│   └── index.html             # HTML5 Single-Page Application
├── install.sh                 # Debian/Ubuntu automated installer
├── uninstall.sh               # Complete clean uninstaller
├── run.py                     # Programmatic launch script
├── pulsearr.bat               # Windows 1-click batch launcher
└── README.md                  # Comprehensive Documentation
```

---

## 🔌 API Endpoints Summary

- `GET  /api/v1/series` — List all shows with season & episode progress
- `POST /api/v1/series` — Add show from TVMaze with complete seasons & episodes
- `GET  /api/v1/series/{id}` — Full show detail, seasons accordion, episodes table
- `GET  /api/v1/movies` — List all movies in the library
- `POST /api/v1/movies` — Add movie to monitored library
- `GET  /api/v1/movies/{id}` — Full movie details and status
- `GET  /api/v1/trackers` — Prowlarr hub: list trackers with capabilities and latency
- `POST /api/v1/trackers/test-all` — Benchmark all trackers concurrently
- `GET  /api/v1/download-clients` — List local & remote download clients
- `POST /api/v1/download-clients` — Add download client with remote path mapping & SSL
- `GET  /api/v1/search/tvmaze?q={name}` — Instant TVMaze show typeahead
- `GET  /api/v1/search/movies?q={name}` — Instant movie typeahead
- `GET  /api/v1/search/releases` — Interactive multi-indexer search for TV or Movies
- `POST /api/v1/search/grab` — Dispatch release candidate to download client
- `GET  /api/v1/queue` — Live unified download queue with speeds and ETA
- `GET  /api/v1/calendar` — Upcoming airing schedule
- `GET  /api/v1/history` — Audit event log (grabs, imports, deletes)
- `GET  /api/v1/system/status` — Live resource metrics and library statistics
- `GET  /api/v1/system/events` — Server-Sent Events (SSE) real-time stream

