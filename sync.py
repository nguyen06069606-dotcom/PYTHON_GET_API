"""Run one DummyJSON products sync: python -m sync"""
from app.database import SessionLocal
from app.main import bootstrap
from app.sync_service import sync_products

bootstrap()
db = SessionLocal()
try:
    run = sync_products(db)
    print(f"run_id={run.id} status={run.status} received={run.items_received} upserted={run.items_inserted_or_updated}")
    if run.status != "succeeded":
        raise SystemExit(1)
finally:
    db.close()

