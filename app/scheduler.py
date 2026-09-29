"""Run one product sync at startup and then every configured interval."""
import logging
import threading
import time

from app.config import settings
from app.database import SessionLocal
from app.sync_service import sync_products

logging.basicConfig(level=settings.log_level.upper(),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("dummyjson_sync.scheduler")
stop_event = threading.Event()

def main() -> None:
    interval = max(60, settings.sync_interval_seconds)
    log.info("Scheduler started; interval_seconds=%s", interval)
    while not stop_event.is_set():
        cycle_started = time.monotonic()
        db = SessionLocal()
        try:
            run = sync_products(db)
            if run.status == "succeeded":
                log.info("Sync succeeded; run_id=%s received=%s upserted=%s",
                         run.id, run.items_received, run.items_inserted_or_updated)
            else:
                log.error("Sync failed; run_id=%s error=%s", run.id, run.error_message)
        except Exception:
            log.exception("Unexpected error while syncing products")
        finally:
            db.close()
        delay = max(0, interval - (time.monotonic() - cycle_started))
        log.info("Next sync in approximately %s seconds", int(delay))
        stop_event.wait(delay)
    log.info("Scheduler stopped")

if __name__ == "__main__":
    main()

