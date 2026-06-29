"""
Scoring_Engine: Tính toán và phân loại điểm số từ kết quả AI phân tích CV.

Nhận dict raw từ AI response, map sang Scores model với:
- overall_classification: 0–49 → Cần cải thiện đáng kể, 50–69 → Cần cải thiện,
                          70–84 → Khá tốt, 85–100 → Xuất sắc
- match_classification:   0–39 → Thấp, 40–69 → Trung bình, 70–100 → Cao
                          (chỉ tính khi có match_score)
"""

from __future__ import annotations

from typing import Any

from models.schemas import MatchClassification, OverallClassification, Scores


def _clamp_score(value: Any) -> int | None:
    """
    Chuyển đổi giá trị score sang int hợp lệ trong [0, 100].
    Trả về None nếu giá trị là None, không thể convert, hoặc ngoài range.
    """
    if value is None:
        return None
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 100:
        return None
    return score


def _classify_overall(score: int) -> OverallClassification:
    """
    Phân loại Overall_Score theo ngưỡng (inclusive boundaries):
      0–49  → Cần cải thiện đáng kể
      50–69 → Cần cải thiện
      70–84 → Khá tốt
      85–100 → Xuất sắc
    """
    if score <= 49:
        return OverallClassification.NEEDS_MAJOR_IMPROVEMENT
    if score <= 69:
        return OverallClassification.NEEDS_IMPROVEMENT
    if score <= 84:
        return OverallClassification.GOOD
    return OverallClassification.EXCELLENT


def _classify_match(score: int) -> MatchClassification:
    """
    Phân loại Match_Score theo ngưỡng (inclusive boundaries):
      0–39  → Thấp
      40–69 → Trung bình
      70–100 → Cao
    """
    if score <= 39:
        return MatchClassification.LOW
    if score <= 69:
        return MatchClassification.MEDIUM
    return MatchClassification.HIGH


def compute_scores(raw_result: dict[str, Any]) -> Scores:
    """
    Map giá trị từ AI response dict sang Scores model.

    Args:
        raw_result: Dict chứa các key từ JSON response của AI:
                    skill_score, structure_score, content_score,
                    overall_score, match_score (tất cả optional)

    Returns:
        Scores instance với các classification đã được tính toán.
        Giá trị None hoặc ngoài range [0, 100] được xử lý gracefully (→ None).
    """
    skill_score = _clamp_score(raw_result.get("skill_score"))
    structure_score = _clamp_score(raw_result.get("structure_score"))
    content_score = _clamp_score(raw_result.get("content_score"))
    overall_score = _clamp_score(raw_result.get("overall_score"))
    match_score = _clamp_score(raw_result.get("match_score"))

    overall_classification = (
        _classify_overall(overall_score) if overall_score is not None else None
    )

    match_classification = (
        _classify_match(match_score) if match_score is not None else None
    )

    return Scores(
        skill_score=skill_score,
        structure_score=structure_score,
        content_score=content_score,
        overall_score=overall_score,
        match_score=match_score,
        overall_classification=overall_classification,
        match_classification=match_classification,
    )
