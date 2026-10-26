import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from ..metadata.tvmaze import tvmaze_client
from ..metadata.movies import movie_metadata_client
from ..indexers.manager import indexer_manager
from ..downloader.manager import download_manager
from ..models import ReleaseCandidate
from pydantic import BaseModel

logger = logging.getLogger("pulsearr.api.search")
router = APIRouter(prefix="/search", tags=["Search"])

class GrabPayload(BaseModel):
    candidate: ReleaseCandidate
    media_type: str = "tv"  # tv or movie
    series_id: Optional[int] = None
    movie_id: Optional[int] = None
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    client_id: Optional[int] = None

@router.get("/tvmaze")
async def search_tvmaze(q: str = Query(..., min_length=1)):
    """Instant typeahead search for TV shows via TVMaze."""
    results = await tvmaze_client.search_shows(q)
    return results

@router.get("/movies")
async def search_movies(q: str = Query(..., min_length=1)):
    """Instant typeahead search for movies via Movie Metadata Provider."""
    results = await movie_metadata_client.search_movies(q)
    return results

@router.get("/releases", response_model=List[ReleaseCandidate])
async def search_releases(
    query: str = Query(...),
    media_type: str = Query("tv"),
    season: Optional[int] = Query(None),
    episode: Optional[int] = Query(None),
    profile_id: int = Query(1)
):
    """Interactive multi-indexer search for TV or Movie releases."""
    candidates = await indexer_manager.search_all(
        query=query,
        season=season,
        episode=episode,
        media_type=media_type,
        profile_id=profile_id
    )
    return candidates

@router.post("/grab")
async def grab_release(payload: GrabPayload):
    """Sends selected release candidate to download client (supporting TV and Movies)."""
    try:
        res = await download_manager.grab_release(
            candidate=payload.candidate,
            media_type=payload.media_type,
            series_id=payload.series_id,
            movie_id=payload.movie_id,
            season_number=payload.season_number,
            episode_number=payload.episode_number,
            client_id=payload.client_id
        )
        return {"status": "success", **res}
    except Exception as e:
        logger.exception("Failed to grab release")
        raise HTTPException(status_code=500, detail=str(e))
