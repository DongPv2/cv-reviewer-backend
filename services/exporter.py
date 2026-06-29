"""
PDF Exporter — tạo báo cáo đánh giá CV dạng PDF từ AnalysisReport.
Dùng Arial Unicode để hỗ trợ tiếng Việt.
"""

import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from models.schemas import AnalysisReport


# ---------------------------------------------------------------------------
# Đăng ký font Unicode hỗ trợ tiếng Việt
# ---------------------------------------------------------------------------
_FONT_REGULAR = "ArialUnicode"
_FONT_BOLD = "ArialUnicode"  # fallback — Arial Unicode không có bold riêng

try:
    pdfmetrics.registerFont(TTFont("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf"))
    _FONT_REGISTERED = True
except Exception:
    _FONT_REGISTERED = False
    _FONT_REGULAR = "Helvetica"
    _FONT_BOLD = "Helvetica-Bold"


# ---------------------------------------------------------------------------
# Màu sắc
# ---------------------------------------------------------------------------
COLOR_PRIMARY   = colors.HexColor("#1e3a5f")   # xanh navy đậm
COLOR_ACCENT    = colors.HexColor("#2563eb")   # xanh dương
COLOR_SUCCESS   = colors.HexColor("#16a34a")   # xanh lá
COLOR_WARNING   = colors.HexColor("#d97706")   # cam
COLOR_DANGER    = colors.HexColor("#dc2626")   # đỏ
COLOR_LIGHT_BG  = colors.HexColor("#f8fafc")   # xám nhạt
COLOR_ROW_ALT   = colors.HexColor("#eff6ff")   # xanh nhạt cho row alt
COLOR_BORDER    = colors.HexColor("#cbd5e1")
COLOR_HEADER_BG = colors.HexColor("#1e3a5f")
COLOR_TEXT      = colors.HexColor("#1e293b")
COLOR_MUTED     = colors.HexColor("#64748b")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classification_color(cls_text: Optional[str]) -> colors.Color:
    if not cls_text:
        return COLOR_MUTED
    if "Xuất sắc" in cls_text:
        return COLOR_SUCCESS
    if "Khá tốt" in cls_text:
        return COLOR_ACCENT
    if "đáng kể" in cls_text:
        return COLOR_DANGER
    if "Cần cải thiện" in cls_text:
        return COLOR_WARNING
    if cls_text == "Cao":
        return COLOR_SUCCESS
    if cls_text == "Trung bình":
        return COLOR_WARNING
    if cls_text == "Thấp":
        return COLOR_DANGER
    return COLOR_MUTED


def _score_label(score: Optional[int]) -> str:
    if score is None:
        return "N/A"
    if score >= 85:
        return "Xuất sắc"
    if score >= 70:
        return "Khá tốt"
    if score >= 50:
        return "Cần cải thiện"
    return "Cần cải thiện đáng kể"


def _category_color(category: str) -> colors.Color:
    mapping = {
        "Kỹ năng": colors.HexColor("#1d4ed8"),
        "Cấu trúc": colors.HexColor("#7c3aed"),
        "Nội dung": colors.HexColor("#15803d"),
        "Phù hợp với công việc": colors.HexColor("#c2410c"),
    }
    return mapping.get(category, COLOR_MUTED)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ExportError(Exception):
    pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_pdf(report: AnalysisReport, file_name: str) -> bytes:
    """
    Tạo PDF báo cáo đánh giá CV đẹp, hỗ trợ tiếng Việt.

    Returns:
        bytes — nội dung file PDF

    Raises:
        ExportError
    """
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.2 * cm,
            bottomMargin=2 * cm,
        )

        W = A4[0] - 4 * cm  # chiều rộng nội dung

        # ── Styles ──────────────────────────────────────────────────────────
        def s(name, **kw):
            return ParagraphStyle(name, **kw)

        style_title = s("title", fontName=_FONT_REGULAR, fontSize=22, leading=28, textColor=COLOR_PRIMARY, spaceAfter=2)
        style_subtitle = s("subtitle", fontName=_FONT_REGULAR, fontSize=10, leading=14, textColor=COLOR_MUTED, spaceAfter=16)
        style_section = s("section", fontName=_FONT_BOLD, fontSize=13, leading=18, textColor=COLOR_PRIMARY, spaceBefore=18, spaceAfter=8)
        style_body = s("body", fontName=_FONT_REGULAR, fontSize=10, leading=15, textColor=COLOR_TEXT, spaceAfter=3)
        style_muted = s("muted", fontName=_FONT_REGULAR, fontSize=9, leading=13, textColor=COLOR_MUTED)
        style_cell = s("cell", fontName=_FONT_REGULAR, fontSize=9, leading=13, textColor=COLOR_TEXT)
        style_cell_bold = s("cell_bold", fontName=_FONT_BOLD, fontSize=9, leading=13, textColor=COLOR_TEXT)

        story = []

        # ── Header ──────────────────────────────────────────────────────────
        story.append(Paragraph("Báo cáo đánh giá CV", style_title))
        story.append(Paragraph(f"File: {file_name}", style_subtitle))
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceAfter=8))

        # ── Scores table ─────────────────────────────────────────────────────
        story.append(Paragraph("Điểm số đánh giá", style_section))

        scores = report.scores

        def score_row(label: str, score: Optional[int], cls: Optional[str] = None) -> list:
            cls_str = cls or (_score_label(score) if score is not None else "N/A")
            score_str = str(score) if score is not None else "N/A"
            cls_color = _classification_color(cls_str)
            return [
                Paragraph(label, style_cell),
                Paragraph(f"<b>{score_str}</b>", style_cell_bold),
                Paragraph(f'<font color="{cls_color.hexval() if hasattr(cls_color, "hexval") else "#64748b"}">{cls_str}</font>', style_cell),
            ]

        # Tạo màu cho classification cell bằng cách dùng text thường
        def score_row_plain(label: str, score: Optional[int], cls: Optional[str] = None) -> list:
            cls_str = cls or (_score_label(score) if score is not None else "N/A")
            score_str = str(score) if score is not None else "N/A"
            return [label, score_str, cls_str]

        score_data = [["Tiêu chí", "Điểm", "Xếp loại"]]

        rows_meta = []
        if scores.overall_score is not None:
            cls = scores.overall_classification.value if scores.overall_classification else None
            score_data.append(score_row_plain("Tổng thể (Overall)", scores.overall_score, cls))
            rows_meta.append((scores.overall_score, cls))
        if scores.skill_score is not None:
            score_data.append(score_row_plain("Kỹ năng (Skill)", scores.skill_score))
            rows_meta.append((scores.skill_score, None))
        if scores.structure_score is not None:
            score_data.append(score_row_plain("Cấu trúc (Structure)", scores.structure_score))
            rows_meta.append((scores.structure_score, None))
        if scores.content_score is not None:
            score_data.append(score_row_plain("Nội dung (Content)", scores.content_score))
            rows_meta.append((scores.content_score, None))
        if scores.match_score is not None:
            cls = scores.match_classification.value if scores.match_classification else None
            score_data.append(score_row_plain("Phù hợp JD (Match)", scores.match_score, cls))
            rows_meta.append((scores.match_score, cls))

        # Thêm tiêu chí tùy chỉnh
        if report.criteria_scores:
            for criterion, score_val in report.criteria_scores.items():
                score_data.append(score_row_plain(criterion, score_val))
                rows_meta.append((score_val, None))

        col_w = [W * 0.45, W * 0.15, W * 0.40]
        score_table = Table(score_data, colWidths=col_w)

        # Build table style commands
        ts_cmds = [
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            # Data rows
            ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("TOPPADDING", (0, 1), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            # Border
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("LINEBELOW", (0, 0), (-1, 0), 1, COLOR_HEADER_BG),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ROW_ALT]),
        ]

        # Tô màu cột điểm và xếp loại theo ngưỡng
        for i, (score_val, cls_override) in enumerate(rows_meta, start=1):
            cls_text = cls_override or _score_label(score_val)
            c = _classification_color(cls_text)
            ts_cmds.append(("TEXTCOLOR", (1, i), (1, i), c))
            ts_cmds.append(("TEXTCOLOR", (2, i), (2, i), c))
            ts_cmds.append(("FONTNAME", (1, i), (1, i), _FONT_BOLD))

        score_table.setStyle(TableStyle(ts_cmds))
        story.append(score_table)
        story.append(Spacer(1, 0.3 * cm))

        # ── Overall classification badge ─────────────────────────────────────
        if scores.overall_classification:
            story.append(Paragraph("Xếp loại tổng thể", style_section))
            cls_val = scores.overall_classification.value
            cls_color = _classification_color(cls_val)
            badge_style = ParagraphStyle(
                "badge_dyn",
                fontName=_FONT_BOLD,
                fontSize=13,
                leading=18,
                textColor=cls_color,
                spaceAfter=6,
            )
            story.append(Paragraph(f"★  {cls_val}", badge_style))

        # ── Criteria scores (nếu có tiêu chí tùy chỉnh) ────────────────────
        if report.criteria and report.criteria_scores:
            story.append(Paragraph("Đánh giá theo tiêu chí", style_section))
            c_data = [["Tiêu chí tuyển chọn", "Điểm", "Nhận xét"]]
            c_meta = []
            for criterion in report.criteria:
                score_val = report.criteria_scores.get(criterion)
                cls_text = _score_label(score_val)
                c_data.append([criterion, str(score_val) if score_val is not None else "N/A", cls_text])
                c_meta.append((score_val, None))

            c_table = Table(c_data, colWidths=[W * 0.50, W * 0.15, W * 0.35])
            c_ts = [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (1, 0), (2, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ("TOPPADDING", (0, 1), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ROW_ALT]),
            ]
            for i, (sv, _) in enumerate(c_meta, start=1):
                ct = _score_label(sv)
                cc = _classification_color(ct)
                c_ts.append(("TEXTCOLOR", (1, i), (1, i), cc))
                c_ts.append(("TEXTCOLOR", (2, i), (2, i), cc))
                c_ts.append(("FONTNAME", (1, i), (1, i), _FONT_BOLD))
            c_table.setStyle(TableStyle(c_ts))
            story.append(c_table)
            story.append(Spacer(1, 0.3 * cm))

        # ── Missing skills ──────────────────────────────────────────────────
        if report.missing_skills:
            story.append(Paragraph("Kỹ năng còn thiếu", style_section))
            for skill in report.missing_skills:
                story.append(Paragraph(f"•  {skill}", style_body))
            story.append(Spacer(1, 0.2 * cm))

        # ── Recommendations ─────────────────────────────────────────────────
        if report.recommendations:
            story.append(Paragraph("Đề xuất cải thiện", style_section))

            col_w_rec = [W * 0.05, W * 0.16, W * 0.25, W * 0.54]

            style_rec_idx = ParagraphStyle("rec_idx", fontName=_FONT_REGULAR, fontSize=9, leading=13, textColor=COLOR_MUTED, alignment=1)
            style_rec_title = ParagraphStyle("rec_title", fontName=_FONT_REGULAR, fontSize=9, leading=14, textColor=COLOR_TEXT, wordWrap="CJK")
            style_rec_action = ParagraphStyle("rec_action", fontName=_FONT_REGULAR, fontSize=9, leading=14, textColor=COLOR_TEXT, wordWrap="CJK")

            header_style = ParagraphStyle("rec_hdr", fontName=_FONT_BOLD, fontSize=10, leading=14, textColor=colors.white)

            rec_data = [[
                Paragraph("#", header_style),
                Paragraph("Danh mục", header_style),
                Paragraph("Tiêu đề", header_style),
                Paragraph("Hành động cụ thể", header_style),
            ]]
            sorted_recs = sorted(report.recommendations, key=lambda r: r.priority)

            for idx, rec in enumerate(sorted_recs, start=1):
                cat_color = _category_color(rec.category.value)
                cat_style = ParagraphStyle(
                    f"cat_{idx}",
                    fontName=_FONT_BOLD,
                    fontSize=9,
                    leading=13,
                    textColor=cat_color,
                )
                rec_data.append([
                    Paragraph(str(idx), style_rec_idx),
                    Paragraph(rec.category.value, cat_style),
                    Paragraph(rec.title, style_rec_title),
                    Paragraph(rec.action, style_rec_action),
                ])

            rec_table = Table(
                rec_data,
                colWidths=col_w_rec,
                repeatRows=1,
            )
            rec_ts = [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                # Data
                ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 1), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ROW_ALT]),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("LINEBELOW", (0, 0), (-1, 0), 1, COLOR_HEADER_BG),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, COLOR_BORDER),
            ]

            rec_table.setStyle(TableStyle(rec_ts))
            story.append(rec_table)

        # ── Footer ──────────────────────────────────────────────────────────
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
        story.append(Paragraph("Được tạo bởi CV Reviewer AI", style_muted))

        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    except Exception as e:
        raise ExportError(str(e)) from e
