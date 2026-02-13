import asyncio
from contextlib import suppress

from src.management.logger import configure_logger
from src.management.settings import get_settings
from src.services.peers_service import get_peers_service


logger = configure_logger("SyncScheduler", "yellow")


class SyncScheduler:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.peers_service = get_peers_service()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def _run(self) -> None:
        interval = max(1, self.settings.sync_interval_seconds)
        logger.info(f"Sync scheduler started with interval {interval}s")

        while not self._stop_event.is_set():
            try:
                synced = await self.peers_service.sync_peers_status()
                logger.debug(f"Sync iteration completed, protocol payloads sent: {synced}")
            except Exception as exc:
                logger.error(f"Sync iteration failed: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

        logger.info("Sync scheduler stopped")
