from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import requests
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Product, SyncRun

def sync_products(db: Session) -> SyncRun:
    run = SyncRun(status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        all_products: list[dict] = []
        skip = 0
        total = None
        with requests.Session() as client:
            while total is None or skip < total:
                response = client.get(f"{settings.dummyjson_base_url.rstrip('/')}/products",
                    params={"limit": settings.sync_page_size, "skip": skip},
                    timeout=settings.dummyjson_timeout_seconds)
                response.raise_for_status()
                page = response.json()
                items = page.get("products")
                if not isinstance(items, list):
                    raise ValueError("DummyJSON response has no products list")
                total = int(page.get("total", 0))
                all_products.extend(items)
                if not items:
                    break
                skip += len(items)

        run.items_received = len(all_products)
        now = datetime.now(timezone.utc)
        for start in range(0, len(all_products), 500):
            batch = []
            for p in all_products[start:start + 500]:
                batch.append({
                    "id": int(p["id"]), "title": str(p["title"]), "description": str(p.get("description", "")),
                    "category": str(p.get("category", "uncategorized")), "price": Decimal(str(p.get("price", 0))),
                    "discount_percentage": Decimal(str(p.get("discountPercentage", 0))),
                    "rating": Decimal(str(p.get("rating", 0))), "stock": int(p.get("stock", 0)),
                    "brand": p.get("brand"), "sku": str(p.get("sku", "")),
                    "thumbnail": str(p.get("thumbnail", "")),
                    "source_updated_at": str(p.get("meta", {}).get("updatedAt", "")) or None,
                    "raw_data": p, "synced_at": now,
                })
            if batch:
                stmt = insert(Product).values(batch)
                stmt = stmt.on_conflict_do_update(index_elements=[Product.id], set_={
                    key: getattr(stmt.excluded, key) for key in batch[0] if key != "id"
                })
                db.execute(stmt)
        run.items_inserted_or_updated = len(all_products)
        run.status = "succeeded"
    except (requests.RequestException, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        db.rollback()
        run = db.get(SyncRun, run.id)
        run.status = "failed"
        run.error_message = str(exc)[:2000]
    except Exception:
        db.rollback()
        run = db.get(SyncRun, run.id)
        run.status = "failed"
        run.error_message = "Unexpected error during sync"
        db.commit()
        raise
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run

