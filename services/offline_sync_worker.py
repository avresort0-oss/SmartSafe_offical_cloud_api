import threading
import time
import logging
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Explicitly add project root to sys.path

from core.database import SessionLocal
from services.sync_service import SyncService

logger = logging.getLogger(__name__)

class OfflineSyncWorker:
    """Daemon thread worker that orchestrates the periodic data sync pipeline."""
    def __init__(self, interval_seconds: int = 10):
        self.running = False
        self.thread = None
        self.interval = interval_seconds
        self._stop_event = threading.Event()

    def start(self):
        if not self.running:
            self.running = True
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run(self):
        while self.running:
            try:
                sync_service = SyncService()
                synced_count = sync_service.push_unsynced_messages()
                deleted_count = sync_service.push_deletions()
                
                if synced_count > 0:
                    logger.info(f"[Sync Engine] Successfully pushed {synced_count} encrypted messages to cloud.")
                if deleted_count > 0:
                    logger.info(f"[Sync Engine] Successfully propagated {deleted_count} message deletions to cloud.")
            except Exception as e:
                logger.error(f"[Sync Engine] Error during sync operation: {e}", exc_info=True)
            
            self._stop_event.wait(self.interval) # Replaces blocking time.sleep()