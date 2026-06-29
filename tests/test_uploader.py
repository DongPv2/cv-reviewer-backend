"""
Unit tests cho CV_Uploader — hàm validate_upload.

Coverage:
  - Extension hợp lệ: .pdf, .docx, .txt (Req 1.1, 1.3)
  - Extension không hợp lệ: .exe, .png (Req 1.1, 1.3)
  - Extension uppercase: .PDF, .DOCX (Req 1.1)
  - Kích thước file vượt 10 MB (Req 1.2, 1.4)
  - Kích thước file đúng 10 MB — hợp lệ (Req 1.2)
  - JD là None → trả (None, None) (Req 3.5, 3.6)
  - JD chỉ chứa whitespace → trả (None, None) (Req 3.6)
  - JD > 5000 ký tự → raise ValueError (Req 3.5)
  - JD đúng 5000 ký tự → hợp lệ, trả về trimmed (Req 3.5)
  - JD hợp lệ → trả về trimmed (Req 3.5, 3.6)
  - JD có leading/trailing whitespace → trả về trimmed (Req 3.6)
"""

import pytest

from backend.services.uploader import validate_upload

# ---------------------------------------------------------------------------
# Hằng số dùng trong tests
# ---------------------------------------------------------------------------
MAX_BYTES = 10 * 1024 * 1024          # 10 MB tính bằng bytes
OVER_MAX_BYTES = MAX_BYTES + 1        # Vượt giới hạn 1 byte
MAX_JD_LENGTH = 5000
SMALL_SIZE = 1024                     # 1 KB — luôn hợp lệ


# ===========================================================================
# Nhóm 1: Kiểm tra extension file
# ===========================================================================

class TestFileExtension:
    """Tests cho Requirement 1.1, 1.3: validate extension file."""

    def test_pdf_valid(self):
        """File .pdf hợp lệ → trả (None, None)."""
        validated_jd, error = validate_upload("resume.pdf", SMALL_SIZE, None)
        assert error is None
        assert validated_jd is None

    def test_docx_valid(self):
        """File .docx hợp lệ → trả (None, None)."""
        validated_jd, error = validate_upload("cv.docx", SMALL_SIZE, None)
        assert error is None
        assert validated_jd is None

    def test_txt_valid(self):
        """File .txt hợp lệ → trả (None, None)."""
        validated_jd, error = validate_upload("my_cv.txt", SMALL_SIZE, None)
        assert error is None
        assert validated_jd is None

    def test_exe_raises_value_error(self):
        """Extension .exe không được hỗ trợ → raise ValueError với mention PDF/DOCX/TXT."""
        with pytest.raises(ValueError) as exc_info:
            validate_upload("malware.exe", SMALL_SIZE, None)
        msg = str(exc_info.value).lower()
        # Message phải đề cập đến ít nhất một trong các định dạng hợp lệ
        assert any(fmt in msg for fmt in ["pdf", "docx", "txt"])

    def test_png_raises_value_error(self):
        """Extension .png không được hỗ trợ → raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_upload("photo.png", SMALL_SIZE, None)
        msg = str(exc_info.value).lower()
        assert any(fmt in msg for fmt in ["pdf", "docx", "txt"])

    def test_uppercase_pdf_is_accepted(self):
        """Extension .PDF (uppercase) phải được chấp nhận."""
        validated_jd, error = validate_upload("Resume.PDF", SMALL_SIZE, None)
        assert error is None

    def test_uppercase_docx_is_accepted(self):
        """Extension .DOCX (uppercase) phải được chấp nhận."""
        validated_jd, error = validate_upload("CV.DOCX", SMALL_SIZE, None)
        assert error is None


# ===========================================================================
# Nhóm 2: Kiểm tra kích thước file
# ===========================================================================

class TestFileSize:
    """Tests cho Requirement 1.2, 1.4: validate kích thước file."""

    def test_file_over_10mb_raises_value_error(self):
        """File vượt 10 MB (MAX_BYTES + 1) → raise ValueError với mention '10 MB'."""
        with pytest.raises(ValueError) as exc_info:
            validate_upload("big.pdf", OVER_MAX_BYTES, None)
        msg = str(exc_info.value)
        # Message phải đề cập đến giới hạn 10 MB
        assert "10" in msg

    def test_file_exactly_10mb_is_valid(self):
        """File đúng 10 MB (MAX_BYTES) → hợp lệ, không raise."""
        validated_jd, error = validate_upload("exact.pdf", MAX_BYTES, None)
        assert error is None

    def test_file_under_10mb_is_valid(self):
        """File nhỏ hơn 10 MB → hợp lệ."""
        validated_jd, error = validate_upload("small.pdf", SMALL_SIZE, None)
        assert error is None


# ===========================================================================
# Nhóm 3: Kiểm tra Job Description (JD)
# ===========================================================================

class TestJobDescription:
    """Tests cho Requirement 3.5, 3.6: validate và chuẩn hóa JD."""

    def test_jd_none_returns_none(self):
        """JD là None → trả (None, None), không lỗi."""
        validated_jd, error = validate_upload("cv.pdf", SMALL_SIZE, None)
        assert validated_jd is None
        assert error is None

    def test_jd_whitespace_only_returns_none(self):
        """JD chỉ chứa whitespace ('  \\n  \\t  ') → coi như không có JD, trả None."""
        validated_jd, error = validate_upload("cv.pdf", SMALL_SIZE, "  \n  \t  ")
        assert validated_jd is None
        assert error is None

    def test_jd_over_5000_chars_raises_value_error(self):
        """JD vượt 5000 ký tự → raise ValueError với mention '5000'."""
        long_jd = "a" * (MAX_JD_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            validate_upload("cv.pdf", SMALL_SIZE, long_jd)
        msg = str(exc_info.value)
        assert "5000" in msg

    def test_jd_exactly_5000_chars_is_valid(self):
        """JD đúng 5000 ký tự → hợp lệ, trả về JD đã trimmed."""
        exact_jd = "b" * MAX_JD_LENGTH
        validated_jd, error = validate_upload("cv.pdf", SMALL_SIZE, exact_jd)
        assert error is None
        assert validated_jd == exact_jd

    def test_jd_valid_returns_trimmed(self):
        """JD hợp lệ → trả về JD đúng nội dung (trimmed)."""
        jd = "Looking for a Python developer with 3 years of experience."
        validated_jd, error = validate_upload("cv.pdf", SMALL_SIZE, jd)
        assert error is None
        assert validated_jd == jd

    def test_jd_with_leading_trailing_whitespace_returns_trimmed(self):
        """JD có khoảng trắng đầu/cuối → trả về phiên bản đã trimmed."""
        jd_raw = "  Senior Backend Engineer required.  "
        jd_expected = jd_raw.strip()
        validated_jd, error = validate_upload("cv.pdf", SMALL_SIZE, jd_raw)
        assert error is None
        assert validated_jd == jd_expected
