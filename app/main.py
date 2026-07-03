from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging
import os
import secrets
from datetime import datetime, timezone
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.ratelimit import get_client_ip
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.api.v1 import router
from app.db.database import AsyncSessionLocal
from app.models.trash import Trash
from app.models.vault_item import VaultItem

logger = logging.getLogger(__name__)


async def _cleanup_expired_trash() -> None:
    """permanent_delete_at süresi geçen trash öğelerini kalıcı olarak siler."""
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Trash).where(Trash.permanent_delete_at <= now)
            )
            expired = result.scalars().all()
            if not expired:
                return
            for trash in expired:
                item_result = await db.execute(
                    select(VaultItem).where(VaultItem.id == trash.vault_item_id)
                )
                item = item_result.scalar_one_or_none()
                if item:
                    await db.delete(item)
                await db.delete(trash)
            await db.commit()
            logger.info("Trash cleanup: %d öğe kalıcı silindi", len(expired))
        except Exception:
            await db.rollback()
            logger.exception("Trash cleanup hatası")


async def _trash_cleanup_loop() -> None:
    """Saatte bir trash temizliği yapar."""
    while True:
        await _cleanup_expired_trash()
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_trash_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


limiter = Limiter(key_func=get_client_ip, default_limits=["200/minute"])

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    # Production'da /docs ve /redoc'u kapat
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "DeniKey API çalışıyor", "version": settings.APP_VERSION}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
