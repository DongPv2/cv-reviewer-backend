"""
Recommendation_Engine: Tạo và sắp xếp danh sách đề xuất cải thiện CV từ kết quả AI.

Quy trình xử lý:
1. Trích xuất danh sách recommendations từ raw_result["recommendations"]
2. Parse từng item thành Recommendation model (bỏ qua item không hợp lệ)
3. Sort tăng dần theo priority (priority=1 là cao nhất, xuất hiện trước)
4. Clamp tối đa 10 items
5. Không pad nếu AI chỉ tìm được < 3 issues (Requirement 5.7)

Lưu ý về category "Phù hợp với công việc":
- Nếu has_job_description=True, AI được kỳ vọng trả về ít nhất 1 item JOB_FIT (Requirement 5.4)
- Recommendation_Engine không tự tạo thêm item — chỉ xử lý đúng những gì AI trả về
"""

from __future__ import annotations

import logging
from typing import Any

from models.schemas import Recommendation, RecommendationCategory, Scores

logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 10


def _parse_recommendation(item: Any) -> Recommendation | None:
    """
    Parse một dict thành Recommendation model.

    Args:
        item: Một entry trong danh sách recommendations từ AI response.

    Returns:
        Recommendation instance nếu parse thành công, None nếu item không hợp lệ.
    """
    if not isinstance(item, dict):
        logger.warning("Bỏ qua recommendation không phải dict: %r", item)
        return None

    try:
        category = RecommendationCategory(item["category"])
        priority = int(item["priority"])
        title = str(item["title"])
        action = str(item["action"])
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Bỏ qua recommendation không hợp lệ (%s): %r", exc, item)
        return None

    try:
        return Recommendation(
            category=category,
            priority=priority,
            title=title,
            action=action,
        )
    except Exception as exc:  # pydantic ValidationError hoặc lỗi khác
        logger.warning("Recommendation không vượt qua validation (%s): %r", exc, item)
        return None


def generate(
    raw_result: dict[str, Any],
    scores: Scores,
    has_job_description: bool = False,
) -> list[Recommendation]:
    """
    Tạo danh sách đề xuất cải thiện CV từ kết quả AI.

    Quy trình:
    - Lấy raw_result["recommendations"] (trả [] nếu None hoặc không phải list)
    - Parse từng item, bỏ qua item không hợp lệ
    - Sort tăng dần theo priority (priority=1 lên đầu)
    - Clamp tối đa 10 items
    - Không pad nếu ít hơn 3 items (Requirement 5.7)

    Args:
        raw_result: Dict từ JSON response của AI. Phải có key "recommendations"
                    là list[dict], mỗi dict gồm category, priority, title, action.
        scores: Scores model đã tính toán (không được dùng trực tiếp để tạo
                recommendations — việc ưu tiên đã được AI xử lý qua priority field).
        has_job_description: True nếu phiên phân tích có kèm Job Description.
                             Khi True, AI được kỳ vọng đã bao gồm ít nhất 1 item
                             category JOB_FIT trong response.

    Returns:
        Danh sách Recommendation đã sort theo priority tăng dần, tối đa 10 items.
        Trả về list rỗng nếu raw_result không chứa recommendations hợp lệ.
    """
    raw_recs = raw_result.get("recommendations")

    if not isinstance(raw_recs, list):
        if raw_recs is not None:
            logger.warning(
                "raw_result['recommendations'] không phải list (type=%s), trả về []",
                type(raw_recs).__name__,
            )
        return []

    # Parse từng item, lọc bỏ item None (không hợp lệ)
    recommendations: list[Recommendation] = []
    for item in raw_recs:
        parsed = _parse_recommendation(item)
        if parsed is not None:
            recommendations.append(parsed)

    # Sort tăng dần theo priority (1 = cao nhất → lên trước)
    recommendations.sort(key=lambda r: r.priority)

    # Clamp tối đa MAX_RECOMMENDATIONS items
    recommendations = recommendations[:MAX_RECOMMENDATIONS]

    if has_job_description:
        has_job_fit = any(
            r.category == RecommendationCategory.JOB_FIT for r in recommendations
        )
        if not has_job_fit:
            logger.warning(
                "has_job_description=True nhưng AI không trả về recommendation "
                "category JOB_FIT. Recommendation_Engine không tự tạo thêm — "
                "đây là trách nhiệm của AI prompt (Requirement 5.4)."
            )

    return recommendations
