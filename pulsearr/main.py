import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .config import config, PULSEARR_DIR
from .database import init_db
from .scheduler.engine import scheduler_engine
from .metadata.tvmaze import tvmaze_client
from .api import api_router

# Configure high-speed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("pulsearr")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initializing Pulsearr database with WAL mode...")
    await init_db()
    logger.info("Starting background scheduler and event engine...")
    await scheduler_engine.start()
    logger.info(f"Pulsearr v{config.version} is ready! Listening at http://localhost:{config.port}")
    yield
    # Shutdown sequence
    logger.info("Stopping Pulsearr background scheduler...")
    await scheduler_engine.stop()
    await tvmaze_client.close()
    logger.info("Pulsearr shutdown complete.")

app = FastAPI(
    title="Pulsearr",
    description="Next-Gen Ultra-Fast Asynchronous Python TV PVR. Better, lighter, and faster than Sonarr.",
    version=config.version,
    lifespan=lifespan
)

# CORS middleware for open local API integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API
app.include_router(api_router)

# Mount Static Files & Templates
STATIC_DIR = PULSEARR_DIR / "static"
TEMPLATES_DIR = PULSEARR_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serves the Pulsearr Web UI Dashboard."""
    return templates.TemplateResponse(request=request, name="index.html", context={"version": config.version})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serves a sleek glowing SVG favicon."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="14" fill="#0d121c" stroke="#6366f1" stroke-width="2"/><circle cx="16" cy="16" r="6" fill="#06b6d4"/></svg>'
    return Response(content=svg, media_type="image/svg+xml")

