import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class TallyFileWatcher:
    """Monitor Tally import/export/XML folders and trigger sync workflows."""

    def __init__(
        self,
        import_folder: str | Path,
        export_folder: str | Path,
        xml_folder: str | Path,
        poll_interval: float = 5.0,
    ):
        self.import_folder = Path(import_folder)
        self.export_folder = Path(export_folder)
        self.xml_folder = Path(xml_folder)
        self.poll_interval = poll_interval
        self._known_files: dict[str, float] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._callbacks: list[Callable[[str, Path, dict[str, Any]], Awaitable[None]]] = []

    def on_file_detected(
        self,
        callback: Callable[[str, Path, dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._callbacks.append(callback)

    async def start(self) -> None:
        for folder in (self.import_folder, self.export_folder, self.xml_folder):
            folder.mkdir(parents=True, exist_ok=True)
            for f in folder.glob("*.xml"):
                self._known_files[str(f)] = f.stat().st_mtime

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("file_watcher_started", import_folder=str(self.import_folder))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("file_watcher_stopped")

    async def _poll_loop(self) -> None:
        while self._running:
            await self._scan_folders()
            await asyncio.sleep(self.poll_interval)

    async def _scan_folders(self) -> None:
        folder_map = {
            "import": self.import_folder,
            "export": self.export_folder,
            "xml": self.xml_folder,
        }
        for folder_type, folder in folder_map.items():
            for xml_file in folder.glob("*.xml"):
                path_key = str(xml_file)
                mtime = xml_file.stat().st_mtime
                if path_key not in self._known_files or self._known_files[path_key] < mtime:
                    self._known_files[path_key] = mtime
                    event = {
                        "folder_type": folder_type,
                        "file_name": xml_file.name,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                        "size_bytes": xml_file.stat().st_size,
                    }
                    logger.info("tally_file_detected", **event)
                    for callback in self._callbacks:
                        try:
                            await callback(folder_type, xml_file, event)
                        except Exception as exc:
                            logger.warning("file_watcher_callback_error", error=str(exc))

    def scan_once(self) -> list[dict[str, Any]]:
        """Synchronous single scan for API-triggered checks."""
        new_files = []
        for folder_type, folder in [
            ("import", self.import_folder),
            ("export", self.export_folder),
            ("xml", self.xml_folder),
        ]:
            for xml_file in folder.glob("*.xml"):
                path_key = str(xml_file)
                mtime = xml_file.stat().st_mtime
                if path_key not in self._known_files or self._known_files[path_key] < mtime:
                    self._known_files[path_key] = mtime
                    new_files.append({
                        "folder_type": folder_type,
                        "path": path_key,
                        "file_name": xml_file.name,
                    })
        return new_files
