"""
SessionStore: Quản lý CVSession in-memory với TTL tự động.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from models.schemas import CVSession
from config import settings


class SessionStore:
    """
    Lưu trữ và quản lý CVSession trong bộ nhớ (in-memory).

    Không thread-safe — đủ dùng cho MVP single-process.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, CVSession] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_expired(self, session: CVSession) -> bool:
        """Trả True nếu session đã vượt quá SESSION_TTL_MINUTES."""
        ttl = timedelta(minutes=settings.session_ttl_minutes)
        now = datetime.now(tz=timezone.utc)
        last_active = session.last_active
        # Đảm bảo last_active có timezone info
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        return (now - last_active) > ttl

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        file_name: str,
        cv_text: str,
        job_description: str | None = None,
    ) -> CVSession:
        """
        Tạo session mới với UUID ngẫu nhiên, status='analyzing'.

        Args:
            file_name: Tên file CV đã upload.
            cv_text: Nội dung văn bản trích xuất từ CV.
            job_description: Mô tả công việc (tuỳ chọn).

        Returns:
            CVSession mới được tạo và lưu vào store.
        """
        now = datetime.now(tz=timezone.utc)
        session = CVSession(
            session_id=str(uuid.uuid4()),
            file_name=file_name,
            extracted_text=cv_text,
            job_description=job_description,
            report=None,
            created_at=now,
            last_active=now,
            status="analyzing",
            error=None,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> CVSession | None:
        """
        Lấy session theo ID.

        Trả None nếu không tồn tại hoặc đã expired (session expired
        vẫn bị giữ trong store cho đến khi cleanup_expired() được gọi).

        Args:
            session_id: UUID của session cần lấy.

        Returns:
            CVSession nếu tìm thấy và chưa expired, ngược lại None.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            return None
        return session

    def update(self, session_id: str, **kwargs: Any) -> CVSession | None:
        """
        Cập nhật các field của session và tự động đặt lại last_active.

        Chỉ cập nhật session còn hiệu lực (chưa expired).

        Args:
            session_id: UUID của session cần cập nhật.
            **kwargs: Các field cần thay đổi (ví dụ: status="complete", report=...).

        Returns:
            CVSession sau khi cập nhật, hoặc None nếu không tìm thấy / đã expired.
        """
        session = self.get(session_id)
        if session is None:
            return None

        # Luôn cập nhật last_active, cho phép kwargs ghi đè nếu cần
        kwargs.setdefault("last_active", datetime.now(tz=timezone.utc))

        updated = session.model_copy(update=kwargs)
        self._sessions[session_id] = updated
        return updated

    def delete(self, session_id: str) -> bool:
        """
        Xóa session khỏi store.

        Args:
            session_id: UUID của session cần xóa.

        Returns:
            True nếu session tồn tại và đã bị xóa, False nếu không tìm thấy.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """
        Xóa tất cả các session đã hết hạn (last_active > SESSION_TTL_MINUTES).

        Returns:
            Số lượng session đã bị xóa.
        """
        expired_ids = [
            sid
            for sid, session in self._sessions.items()
            if self._is_expired(session)
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)
