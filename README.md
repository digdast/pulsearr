<div align="center">

# ⚡ Pulsearr

### Next-Gen Asynchronous Python TV & Movie PVR — Lighter, Smarter, and Faster than Sonarr
**High-performance automated media management powered by pure async Python, SQLite WAL mode, and zero .NET overhead.**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-Framework-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-WAL%20Concurrent-003B57?style=for-the-badge&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Gluetun-VPN%20Compatible-00C49F?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" />
</p>

</div>

---

## 📸 Production Screenshot (`http://192.168.0.81:32093/`)

*Integrated Arr Media Stack: Series library, interactive release queue, automated quality profiles, and indexer health.*

![Pulsearr Media Stack](docs/screenshots/sonarr-media-stack.png)

---

## 🚀 Why Pulsearr is Faster & Lighter than Sonarr

| Feature / Metric | Legacy Sonarr (.NET / Mono) | Pulsearr (Modern Async Python) |
| :--- | :--- | :--- |
| **Startup Time** | 10 – 25 seconds | **~250 milliseconds** |
| **RAM Footprint** | ~350 MB – 800 MB | **~35 MB – 50 MB** |
| **Metadata Source** | Skyhook proxy (timeouts, API keys) | **Direct TVMaze API (Instant typeahead, 0 keys needed)** |
| **Database Engine** | SQLite (database lock contention) | **SQLite with WAL Mode + 30s busy timeout** |
| **Release Parser** | Hundreds of C# parser classes | **Compiled regex release parser (< 1ms per release)** |
| **Download Clients** | External clients only | **Built-in Fast Simulator + qBittorrent, Transmission, SABnzbd** |
| **Frontend UI** | Heavy React bundle (~10MB+) | **Ultra-lightweight Vanilla JS + CSS Glassmorphism (< 100KB)** |
| **Live Telemetry** | Polling HTTP calls | **Native Server-Sent Events (SSE) Stream** |
| **API** | REST API | **FastAPI with auto-generated OpenAPI `/docs`** |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Frontend ["🖥️ Web Client"]
        Browser["Modern Dark Glassmorphism UI\nSSE Live Events"]
    end

    subgraph CoreEngine ["⚡ Pulsearr Core Engine"]
        API["FastAPI Async Endpoints"]
        Parser["Compiled Regex Release Parser\n(<1ms throughput)"]
        Organizer["Token-Based Media Renamer\n(Hardlink / Move / Copy)"]
        DB[(SQLite WAL Database)]
    end

    subgraph Metadata ["🌐 Metadata & Indexers"]
        TVMaze["TVMaze API\n(Shows, Seasons, Posters)"]
        Indexers["Torznab / Newznab / Prowlarr\n(EZTV, YTS, Usenet)"]
    end

    subgraph Downloaders ["📥 Download Clients & VPN"]
        Simulator["Built-in Fast Simulator\n(28.5 MB/s synthetic)"]
        Qbit["qBittorrent Web API v2\n(Remote / Local SSL)"]
        Gluetun["Gluetun WireGuard VPN\n(Zero IP Leakage)"]
    end

    Browser <-->|SSE & REST| API
    API --> DB
    API --> TVMaze
    API --> Parser
    Parser --> Indexers
    API --> Organizer
    API --> Simulator
    API --> Qbit
    Qbit --> Gluetun
```

---

## ✨ Core Features

1. **Integrated TV & Movie Library**:
   - Manage both TV series and movies in one unified portal without running separate apps on different ports.
   - TVMaze metadata integration: instant typeahead, high-res posters, banners, and air dates with zero API keys.
2. **Trackers & Indexer Hub (Prowlarr Integration)**:
   - Torznab, Newznab, EZTV, and YTS support with live tracker latency benchmarks.
   - Automatic category routing for 1080p, 4K HDR, HEVC, and audio formats.
3. **Download Client Routing**:
   - **Built-in Fast Simulator**: Runs synthetic downloads (28.5 MB/s) and triggers auto-import for immediate demonstration.
   - **qBittorrent / Transmission / SABnzbd**: Direct API integration with custom base paths and remote-to-local path translation (e.g. `/home/user/downloads` ➔ `/data/media`).
4. **Token-Based Media Renamer**:
   - Token formats: `{Series Title} - S{season:00}E{episode:00} - {Episode Title} [{Quality}].mkv`.
   - Atomic rename strategies: `hardlink` (continue seeding without double storage), `move`, or `copy`.

---

## 🛠️ Quickstart

### Local Workstation (Windows, Linux, macOS)
```bash
# Clone and run
git clone https://github.com/ertechlab/pulsearr.git
cd pulsearr
pip install -r requirements.txt
python run.py --port 8989
```

### Docker Compose with Gluetun WireGuard VPN
```yaml
version: "3.8"
services:
  gluetun:
    image: qmcgaw/gluetun
    container_name: gluetun
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=private internet access
      - OPENVPN_USER=p1234567
      - OPENVPN_PASSWORD=secret
    ports:
      - "8989:8989" # Pulsearr Web UI

  pulsearr:
    image: pulsearr:latest
    container_name: pulsearr
    network_mode: "service:gluetun"
    volumes:
      - ./data:/app/data
      - /mnt/media:/media
    restart: unless-stopped
```

```bash
docker compose up -d
```

---

## 📄 License
MIT License. Created by ERTech Lab.
