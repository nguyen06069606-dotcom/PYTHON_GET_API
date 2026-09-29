import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_user, require_permission
from app.config import settings
from app.database import SessionLocal, get_db
from app.models import Product, Role, SyncRun, User
from app.schemas import LoginRequest, ProductRead, SyncResult, TokenResponse, UserCreate
from app.security import create_access_token, hash_password, verify_password
from app.sync_service import sync_products

logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger("dummyjson_sync")
ROLE_PERMISSIONS = {
    "reader": ["products:read", "sync:read"],
    "operator": ["products:read", "sync:read", "sync:run"],
    "admin": ["products:read", "sync:read", "sync:run", "users:manage"],
}

def bootstrap() -> None:
    db = SessionLocal()
    try:
        for name, permissions in ROLE_PERMISSIONS.items():
            role = db.query(Role).filter_by(name=name).first()
            if role is None:
                db.add(Role(name=name, permissions=permissions))
        db.commit()
        username, password = settings.bootstrap_admin_username, settings.bootstrap_admin_password
        if username and password:
            user = db.query(User).filter_by(username=username).first()
            if user is None:
                admin = db.query(Role).filter_by(name="admin").one()
                db.add(User(username=username, password_hash=hash_password(password), roles=[admin]))
                db.commit()
                log.info("Bootstrap administrator created")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    yield

app = FastAPI(title="DummyJSON Product Sync API", version="1.0.0", docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=lifespan)

@app.get("/health/live", include_in_schema=False)
def live():
    return {"status": "ok"}

@app.get("/health/ready", include_in_schema=False)
def ready(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ready"}

@app.post("/auth/token", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload.username).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(access_token=create_access_token(user.username),
                         expires_in=settings.jwt_access_token_minutes * 60)

@app.get("/me")
def me(user: User = Depends(current_user)):
    return {"username": user.username, "roles": [r.name for r in user.roles],
            "permissions": sorted({p for r in user.roles for p in r.permissions})}

@app.post("/admin/users", status_code=201)
def create_user(payload: UserCreate, _: User = Depends(require_permission("users:manage")),
                db: Session = Depends(get_db)):
    roles = db.query(Role).filter(Role.name.in_(payload.roles)).all()
    if len(roles) != len(set(payload.roles)):
        raise HTTPException(status_code=422, detail="One or more role names are invalid")
    user = User(username=payload.username, password_hash=hash_password(payload.password), roles=roles)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"username": user.username, "roles": [r.name for r in roles]}

@app.get("/products", response_model=list[ProductRead])
def list_products(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                  category: str | None = None, _: User = Depends(require_permission("products:read")),
                  db: Session = Depends(get_db)):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    return query.order_by(Product.id).offset(skip).limit(limit).all()

@app.post("/admin/sync", response_model=SyncResult)
def trigger_sync(_: User = Depends(require_permission("sync:run")), db: Session = Depends(get_db)):
    run = sync_products(db)
    if run.status != "succeeded":
        raise HTTPException(status_code=502, detail={"message": "Upstream sync failed", "run_id": run.id})
    return SyncResult(run_id=run.id, status=run.status, items_received=run.items_received,
                      items_inserted_or_updated=run.items_inserted_or_updated)

@app.get("/admin/sync-runs")
def sync_history(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                 _: User = Depends(require_permission("sync:read")), db: Session = Depends(get_db)):
    runs = db.query(SyncRun).order_by(SyncRun.id.desc()).offset(skip).limit(limit).all()
    return [{"id": r.id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at,
             "items_received": r.items_received, "items_inserted_or_updated": r.items_inserted_or_updated,
             "error_message": r.error_message} for r in runs]

