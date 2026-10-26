from fastapi import APIRouter
from .series import router as series_router
from .movies import router as movies_router
from .trackers import router as trackers_router
from .search import router as search_router
from .queue import router as queue_router
from .calendar import router as calendar_router
from .history import router as history_router
from .indexers import router as indexers_router
from .download_clients import router as download_clients_router
from .profiles import router as profiles_router
from .system import router as system_router
from .settings import router as settings_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(series_router)
api_router.include_router(movies_router)
api_router.include_router(trackers_router)
api_router.include_router(search_router)
api_router.include_router(queue_router)
api_router.include_router(calendar_router)
api_router.include_router(history_router)
api_router.include_router(indexers_router)
api_router.include_router(download_clients_router)
api_router.include_router(profiles_router)
api_router.include_router(system_router)
api_router.include_router(settings_router)
