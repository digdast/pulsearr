import asyncio
import logging
import json
from typing import Set, Dict, Any, List
from ..database import get_db
from ..downloader.manager import download_manager
from ..indexers.manager import indexer_manager
from ..organizer.file_manager import file_manager
from ..config import config

logger = logging.getLogger("pulsearr.scheduler")

class SchedulerEngine:
    def __init__(self):
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._subscribers: Set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast(self, event_type: str, data: Any):
        """Broadcasts event to all active SSE subscribers."""
        payload = json.dumps({"event": event_type, "data": data})
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    async def start(self):
        self._running = True
        self._tasks.append(asyncio.create_task(self._queue_monitor_loop()))
        self._tasks.append(asyncio.create_task(self._rss_sync_loop()))
        logger.info("Scheduler engine started (queue monitor + RSS sync active).")

    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Scheduler engine stopped.")

    async def _queue_monitor_loop(self):
        """Continuously polls active downloads and auto-imports upon completion."""
        while self._running:
            try:
                await self.poll_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in queue monitor loop: {e}")
            await asyncio.sleep(config.queue_poll_interval_seconds)

    async def poll_queue(self):
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM queue WHERE status = 'downloading'")
            active_items = await cursor.fetchall()
            if not active_items:
                return

            to_import = []
            for item in active_items:
                client = await download_manager.get_client(item["download_client_id"])
                if not client:
                    continue

                client_items = await client.get_items()
                matched = next((ci for ci in client_items if ci["id"] == item["client_item_id"]), None)

                if matched:
                    status = matched["status"]
                    progress = matched["progress"]
                    speed = matched["speed"]
                    eta = matched["eta"]

                    await db.execute(
                        """
                        UPDATE queue
                        SET progress = ?, download_speed = ?, eta = ?, status = ?
                        WHERE id = ?
                        """,
                        (progress, speed, eta, status, item["id"])
                    )

                    await self.broadcast("queue_update", {
                        "id": item["id"],
                        "title": item["title"],
                        "progress": progress,
                        "speed": speed,
                        "eta": eta,
                        "status": status
                    })

                    # If download completed, queue for import
                    if status == "completed" or progress >= 100.0:
                        if config.auto_import:
                            is_movie = (item["media_type"] == "movie" or bool(item["movie_id"])) if "media_type" in item.keys() else False
                            to_import.append((item, client.name, matched.get("save_path"), is_movie))

            await db.commit()

        # Execute imports outside the active queue lock
        for item, client_name, save_path, is_movie in to_import:
            logger.info(f"Download complete for '{item['title']}', starting auto-import...")
            try:
                if is_movie:
                    from ..organizer.movie_manager import movie_file_manager
                    await movie_file_manager.import_movie_download(
                        queue_id=item["id"],
                        source_title=item["title"],
                        movie_id=item["movie_id"],
                        quality=item["quality"],
                        indexer=item["indexer"],
                        download_client=client_name,
                        source_file_path=save_path
                    )
                    await self.broadcast("import_complete", {
                        "media_type": "movie",
                        "title": item["title"],
                        "movie_id": item["movie_id"]
                    })
                else:
                    await file_manager.import_download(
                        queue_id=item["id"],
                        source_title=item["title"],
                        series_id=item["series_id"],
                        season_number=item["season_number"],
                        episode_number=item["episode_number"],
                        quality=item["quality"],
                        indexer=item["indexer"],
                        download_client=client_name,
                        source_file_path=save_path
                    )
                    await self.broadcast("import_complete", {
                        "media_type": "tv",
                        "title": item["title"],
                        "series_id": item["series_id"],
                        "season": item["season_number"],
                        "episode": item["episode_number"]
                    })
            except Exception as e:
                logger.exception(f"Error during auto-import of '{item['title']}': {e}")

    async def _rss_sync_loop(self):
        """Periodically syncs RSS feeds and auto-grabs wanted episodes."""
        while self._running:
            try:
                # Sleep interval first to allow system startup
                await asyncio.sleep(config.rss_sync_interval_minutes * 60)
                await self.sync_rss()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in RSS sync loop: {e}")

    async def sync_rss(self):
        """Fetches latest releases from all indexers and auto-grabs monitored episodes."""
        logger.info("Executing periodic RSS sync across indexers...")
        releases = await indexer_manager.fetch_all_rss()
        if not releases:
            return

        async with get_db() as db:
            # Get monitored missing episodes
            cursor = await db.execute(
                """
                SELECT e.id as episode_id, e.season_number, e.episode_number, s.id as series_id, s.title as series_title, s.quality_profile_id
                FROM episodes e
                JOIN series s ON s.id = e.series_id
                WHERE s.monitored = 1 AND e.monitored = 1 AND e.has_file = 0
                """
            )
            wanted_episodes = await cursor.fetchall()
            
            # Map by (series_title_normalized, season, episode)
            lookup = {}
            for row in wanted_episodes:
                key = (row["series_title"].lower().replace(" ", ""), row["season_number"], row["episode_number"])
                lookup[key] = row

            grabbed_count = 0
            for rel in releases:
                parsed = rel.parsed
                if parsed.clean_title and parsed.season is not None and parsed.episode is not None:
                    norm_title = parsed.clean_title.lower().replace(" ", "")
                    key = (norm_title, parsed.season, parsed.episode)
                    if key in lookup:
                        target = lookup[key]
                        # Check if release meets criteria
                        if not rel.reject_reasons:
                            try:
                                await download_manager.grab_release(
                                    candidate=rel,
                                    series_id=target["series_id"],
                                    season_number=target["season_number"],
                                    episode_number=target["episode_number"]
                                )
                                grabbed_count += 1
                                del lookup[key] # Don't grab multiple for same episode in one cycle
                            except Exception as e:
                                logger.error(f"RSS auto-grab failed: {e}")

            logger.info(f"RSS sync completed: checked {len(releases)} releases, auto-grabbed {grabbed_count} episodes.")

scheduler_engine = SchedulerEngine()
