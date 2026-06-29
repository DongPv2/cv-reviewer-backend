from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from session_store import SessionStore

# ---------------------------------------------------------------------------
# Global session store — shared với routers qua import
# ---------------------------------------------------------------------------
session_store = SessionStore()


# ---------------------------------------------------------------------------
# Lifespan: khởi động/dừng background cleanup task
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời app: start cleanup loop khi startup, cancel khi shutdown."""

    async def _cleanup_loop() -> None:
        while True:
            await asyncio.sleep(300)  # 5 phút
            removed = session_store.cleanup_expired()
            if removed:
                print(f"[SessionStore] Đã dọn {removed} session hết hạn.")

    task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CV Reviewer API",
    description="API phân tích và đánh giá CV sử dụng AI.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from routers.sessions import router as sessions_router  # noqa: E402

app.include_router(sessions_router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Endpoint kiểm tra trạng thái hoạt động của server."""
    return {"status": "ok"}
