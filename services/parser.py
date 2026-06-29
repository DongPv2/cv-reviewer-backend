"""
CV_Parser — trích xuất nội dung văn bản từ file CV.

Module này cung cấp hàm `parse()` để đọc nội dung từ các định dạng
được hỗ trợ: PDF (pdfplumber), DOCX (python-docx), và TXT (UTF-8 / latin-1).

Raises `ParseError` nếu không trích xuất được text hợp lệ từ file
(ví dụ: file bị mã hóa, bị khóa bằng mật khẩu, hoặc bị hỏng).
"""

import io

import pdfplumber
import docx


class ParseError(Exception):
    """
    Exception được raise khi CV_Parser không thể trích xuất text từ file.

    Điều này xảy ra khi:
    - File PDF bị khóa bằng mật khẩu hoặc bị mã hóa
    - File DOCX bị hỏng hoặc không đọc được paragraph nào
    - File TXT không thể decode được hoặc hoàn toàn trống
    """


def parse(file_bytes: bytes, file_extension: str) -> str:
    """
    Trích xuất nội dung văn bản từ file CV.

    Hỗ trợ ba định dạng:
    - PDF: dùng pdfplumber, extract text từng trang rồi nối lại bằng newline
    - DOCX: dùng python-docx, lấy text từ tất cả các paragraph
    - TXT: decode theo UTF-8, fallback sang latin-1 nếu lỗi

    Parameters
    ----------
    file_bytes : bytes
        Nội dung nhị phân của file CV.
    file_extension : str
        Phần mở rộng của file, có thể có hoặc không có dấu chấm đầu,
        ví dụ: "pdf", ".pdf", "docx", ".docx", "txt", ".txt".
        So sánh không phân biệt hoa/thường.

    Returns
    -------
    str
        Toàn bộ nội dung văn bản trích xuất được từ file.

    Raises
    ------
    ParseError
        Nếu không trích xuất được text (kết quả rỗng hoặc chỉ có whitespace),
        hoặc nếu định dạng file không được hỗ trợ.
    """
    # Chuẩn hoá extension: bỏ dấu chấm đầu, lowercase
    ext = file_extension.lstrip(".").lower()

    if ext == "pdf":
        text = _parse_pdf(file_bytes)
    elif ext == "docx":
        text = _parse_docx(file_bytes)
    elif ext == "txt":
        text = _parse_txt(file_bytes)
    else:
        raise ParseError(
            f"Định dạng file '.{ext}' không được hỗ trợ. "
            "Vui lòng upload file PDF, DOCX hoặc TXT."
        )

    if not text or not text.strip():
        raise ParseError(
            "Không thể trích xuất nội dung từ file CV. "
            "Vui lòng kiểm tra file không bị khóa bằng mật khẩu hoặc bị hỏng, "
            "sau đó thử lại với file khác nếu vấn đề vẫn tiếp tục."
        )

    return text


def _parse_pdf(file_bytes: bytes) -> str:
    """
    Trích xuất text từ file PDF dùng pdfplumber.

    Mỗi trang được extract riêng lẻ, sau đó nối lại bằng ký tự newline.
    Trang không có text (ví dụ: trang chứa ảnh scan) sẽ được bỏ qua.

    Parameters
    ----------
    file_bytes : bytes
        Nội dung nhị phân của file PDF.

    Returns
    -------
    str
        Toàn bộ text trích xuất được, hoặc chuỗi rỗng nếu không có gì.
    """
    pages_text: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)

    return "\n".join(pages_text)


def _parse_docx(file_bytes: bytes) -> str:
    """
    Trích xuất text từ file DOCX dùng python-docx.

    Lấy text từ tất cả các paragraph, bỏ qua paragraph rỗng,
    sau đó nối lại bằng ký tự newline.

    Parameters
    ----------
    file_bytes : bytes
        Nội dung nhị phân của file DOCX.

    Returns
    -------
    str
        Toàn bộ text trích xuất được, hoặc chuỗi rỗng nếu không có paragraph nào.
    """
    document = docx.Document(io.BytesIO(file_bytes))

    paragraphs_text: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text
        if text:
            paragraphs_text.append(text)

    return "\n".join(paragraphs_text)


def _parse_txt(file_bytes: bytes) -> str:
    """
    Trích xuất text từ file TXT thuần.

    Thử decode bằng UTF-8 trước; nếu thất bại, fallback sang latin-1.
    latin-1 (ISO-8859-1) có thể decode mọi byte nên sẽ không bao giờ raise lỗi.

    Parameters
    ----------
    file_bytes : bytes
        Nội dung nhị phân của file TXT.

    Returns
    -------
    str
        Nội dung văn bản đã decode.
    """
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")
