"""
CV_Uploader — Module xử lý validate file CV và Job Description trước khi xử lý.

Responsibilities:
  - Kiểm tra extension file: chỉ chấp nhận .pdf, .docx, .txt
  - Kiểm tra kích thước file: tối đa 10 MB (đọc từ config)
  - Validate và chuẩn hóa Job Description:
      * Trim whitespace; trả None nếu chỉ chứa khoảng trắng
      * Raise ValueError nếu JD vượt 5000 ký tự (đọc từ config)

Requirements: 1.1, 1.2, 1.3, 1.4, 3.5, 3.6
"""

from __future__ import annotations

from typing import Optional, Tuple

from config import settings

# Các extension file được chấp nhận (không phân biệt hoa thường)
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})


def validate_upload(
    file_name: str,
    file_size: int,
    job_description: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Validate file CV và Job Description đầu vào.

    Hàm này thực hiện hai nhóm kiểm tra:

    1. **File validation** (raise ValueError nếu lỗi):
       - Extension phải thuộc {.pdf, .docx, .txt}
       - Kích thước không được vượt quá giới hạn cấu hình (mặc định 10 MB)

    2. **JD validation**:
       - JD là None → trả ``None`` (không có JD, không lỗi)
       - JD chỉ chứa whitespace → trả ``None`` (coi như không có JD, Req 3.6)
       - JD > giới hạn cấu hình (mặc định 5000 ký tự) → raise ``ValueError``
       - Hợp lệ → trả JD đã trim

    Args:
        file_name: Tên file gốc, dùng để lấy extension (ví dụ: ``"resume.pdf"``).
        file_size: Kích thước file tính bằng bytes.
        job_description: Chuỗi mô tả công việc do người dùng nhập, hoặc ``None``.

    Returns:
        Tuple ``(validated_jd, error)`` trong đó:
        - ``validated_jd``: JD đã được trim, hoặc ``None`` nếu không có JD hợp lệ.
        - ``error``: Luôn là ``None`` khi hàm trả về bình thường (lỗi được raise).

    Raises:
        ValueError: Nếu file có extension không hỗ trợ, kích thước vượt giới hạn,
            hoặc JD vượt giới hạn ký tự cho phép.

    Examples:
        >>> validated_jd, error = validate_upload("cv.pdf", 1024, None)
        >>> assert error is None and validated_jd is None

        >>> validated_jd, error = validate_upload("cv.pdf", 1024, "  \\n  ")
        >>> assert validated_jd is None and error is None

        >>> validate_upload("cv.exe", 1024, None)
        Traceback (most recent call last):
            ...
        ValueError: Định dạng file không được hỗ trợ. Vui lòng upload file PDF, DOCX hoặc TXT.
    """
    # --- Bước 1: Kiểm tra extension (Requirement 1.1, 1.3) ---
    ext = _get_extension(file_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Định dạng file không được hỗ trợ. "
            "Vui lòng upload file PDF, DOCX hoặc TXT."
        )

    # --- Bước 2: Kiểm tra kích thước file (Requirement 1.2, 1.4) ---
    max_bytes = settings.max_file_size_bytes
    if file_size > max_bytes:
        raise ValueError(
            f"File vượt quá giới hạn kích thước cho phép. "
            f"Vui lòng upload file có dung lượng tối đa {settings.max_file_size_mb} MB."
        )

    # --- Bước 3: Validate Job Description (Requirement 3.5, 3.6) ---
    validated_jd = _validate_job_description(job_description)

    return validated_jd, None


def _get_extension(file_name: str) -> str:
    """Trích xuất extension từ tên file và chuyển về chữ thường.

    Args:
        file_name: Tên file đầy đủ (ví dụ: ``"Resume_2024.PDF"``).

    Returns:
        Extension bao gồm dấu chấm, viết thường (ví dụ: ``".pdf"``).
        Trả về chuỗi rỗng nếu file không có extension.
    """
    dot_index = file_name.rfind(".")
    if dot_index == -1:
        return ""
    return file_name[dot_index:].lower()


def _validate_job_description(job_description: Optional[str]) -> Optional[str]:
    """Chuẩn hóa và validate chuỗi Job Description.

    - Nếu ``job_description`` là ``None`` → trả ``None``.
    - Nếu sau khi trim chỉ còn khoảng trắng (hoặc rỗng) → trả ``None``.
    - Nếu độ dài sau trim > giới hạn cấu hình → raise ``ValueError``.
    - Ngược lại → trả về chuỗi đã được trim.

    Args:
        job_description: Chuỗi JD thô từ người dùng, hoặc ``None``.

    Returns:
        JD đã trim hoặc ``None``.

    Raises:
        ValueError: Nếu JD sau khi trim vượt quá giới hạn ký tự cho phép.
    """
    if job_description is None:
        return None

    trimmed = job_description.strip()

    if not trimmed:
        # Chỉ chứa whitespace → coi như không có JD (Requirement 3.6)
        return None

    max_jd_len = settings.max_jd_length
    if len(trimmed) > max_jd_len:
        raise ValueError(
            f"Mô tả công việc vượt quá giới hạn {max_jd_len} ký tự. "
            f"Vui lòng rút gọn xuống tối đa {max_jd_len} ký tự."
        )

    return trimmed
