"""
API Router cho các endpoint quản lý CV session.

Endpoints:
    POST   /api/sessions                    — Upload CV, tạo session, bắt đầu phân tích
    GET    /api/sessions/{session_id}       — Lấy trạng thái & kết quả phân tích
    GET    /api/sessions/{session_id}/export — Xuất báo cáo dạng PDF
    DELETE /api/sessions/{session_id}       — Xóa session
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Response, UploadFile, Form, HTTPException
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel

from models.schemas import AnalysisReport, CVSession
from services.uploader import validate_upload
from services.parser import parse, ParseError
from services.analyzer import analyze, AnalysisError
from services.scoring import compute_scores
from services.recommender import generate
from services.exporter import generate_pdf, ExportError
from session_store import SessionStore

router = APIRouter(tags=["Sessions"])


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    report: Optional[AnalysisReport] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Dependency — Singleton session store (có thể override khi test)
# ---------------------------------------------------------------------------

def get_session_store() -> SessionStore:
    """Trả về session store toàn cục từ main. Override trong tests."""
    from main import session_store
    return session_store


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def _run_analysis(
    session_id: str,
    cv_text: str,
    job_description: Optional[str],
    criteria: list[str],
    store: SessionStore,
) -> None:
    """
    Chạy toàn bộ pipeline phân tích CV trong background.

    Cập nhật session với kết quả hoặc thông báo lỗi sau khi hoàn thành.
    """
    import traceback
    print(f"[BG] Bắt đầu phân tích session {session_id}", flush=True)
    try:
        # 1. Gọi AI phân tích
        print("[BG] Đang gọi DeepSeek API...", flush=True)
        raw_result = await analyze(cv_text, job_description, criteria)
        print(f"[BG] AI trả về: {raw_result}", flush=True)

        # 2. Tính điểm
        scores = compute_scores(raw_result)
        print(f"[BG] Scores: {scores}", flush=True)

        # 3. Tạo đề xuất
        has_jd = job_description is not None
        recommendations = generate(raw_result, scores, has_job_description=has_jd)

        # 4. Tổng hợp báo cáo
        report = AnalysisReport(
            scores=scores,
            missing_skills=raw_result.get("missing_skills", []),
            recommendations=recommendations,
            has_job_description=job_description is not None,
            criteria_scores=raw_result.get("criteria_scores", {}),
            criteria=criteria,
        )

        # 5. Cập nhật session thành complete
        store.update(session_id, status="complete", report=report)
        print(f"[BG] Hoàn thành session {session_id}", flush=True)

    except AnalysisError as exc:
        print(f"[BG] AnalysisError: {exc}", flush=True)
        store.update(session_id, status="error", error=str(exc))
    except Exception as exc:
        print(f"[BG] Exception: {exc}", flush=True)
        traceback.print_exc()
        store.update(session_id, status="error", error=f"Lỗi nội bộ: {str(exc)}")


# ---------------------------------------------------------------------------
# POST /api/sessions
# ---------------------------------------------------------------------------

@router.post("/sessions", status_code=201)
async def create_session(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    job_description: Optional[str] = Form(default=None),
    criteria: Optional[str] = Form(default=None),
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """
    Upload CV và bắt đầu phân tích.

    - Validate file (extension, kích thước) và job description
    - Parse nội dung CV
    - Tạo session mới
    - Chạy phân tích AI trong background (không block response)
    - Trả ngay session_id và status="analyzing"
    """
    # Đọc file bytes
    file_bytes = await file.read()
    file_name = file.filename or "unknown"
    file_size = len(file_bytes)

    # Lấy extension
    _, ext = os.path.splitext(file_name)

    # 1. Validate upload
    try:
        validated_jd, _ = validate_upload(file_name, file_size, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 2. Parse CV
    try:
        cv_text = parse(file_bytes, ext)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Parse criteria JSON string
    import json as _json
    criteria_list: list[str] = []
    if criteria:
        try:
            criteria_list = _json.loads(criteria)
        except Exception:
            criteria_list = []

    # 3. Tạo session
    session = store.create(file_name, cv_text, validated_jd)

    # 4. Chạy phân tích trong background
    background_tasks.add_task(
        _run_analysis,
        session.session_id,
        cv_text,
        validated_jd,
        criteria_list,
        store,
    )

    # 5. Trả ngay kết quả
    return {"session_id": session.session_id, "status": "analyzing"}


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}", response_model=SessionStatusResponse)
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> SessionStatusResponse:
    """
    Lấy trạng thái và kết quả phân tích của session.

    Trả 404 nếu session không tồn tại hoặc đã hết hạn.
    """
    session = store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session không tồn tại hoặc đã hết hạn",
        )

    # Cập nhật last_active
    store.update(session_id, last_active=datetime.now(timezone.utc))

    return SessionStatusResponse(
        session_id=session_id,
        status=session.status,
        report=session.report,
        error=session.error,
    )


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}/export
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> FastAPIResponse:
    """
    Xuất báo cáo phân tích CV dạng PDF.

    Trả 404 nếu session không tồn tại, 400 nếu phân tích chưa hoàn thành,
    500 nếu xuất PDF thất bại.
    """
    session = store.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session không tồn tại hoặc đã hết hạn",
        )

    if session.report is None:
        raise HTTPException(
            status_code=400,
            detail="Phân tích chưa hoàn thành",
        )

    try:
        pdf_bytes = generate_pdf(session.report, session.file_name)
    except ExportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Tên file cố định theo spec
    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="cv_review.pdf"',
        },
    )


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}", status_code=204, response_class=Response)
async def delete_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> Response:
    """
    Xóa session khỏi store.

    Trả 404 nếu session không tồn tại.
    """
    deleted = store.delete(session_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Session không tồn tại hoặc đã hết hạn",
        )
    return Response(status_code=204)
