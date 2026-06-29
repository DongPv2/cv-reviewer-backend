"""
AI Analyzer service — gọi DeepSeek API để phân tích CV.

Exports:
    AnalysisError       — exception khi AI thất bại
    RawAnalysisResult   — TypedDict chứa kết quả thô từ AI
    analyze             — hàm async thực hiện phân tích
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypedDict

import openai

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Đường dẫn tới thư mục prompts
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_PROMPT_ANALYZE_CV = _PROMPTS_DIR / "analyze_cv.txt"
_PROMPT_MATCH_JD = _PROMPTS_DIR / "match_jd.txt"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AnalysisError(Exception):
    """Raise khi AI thất bại hoặc trả về JSON không hợp lệ."""


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class RecommendationDict(TypedDict):
    """Một đề xuất cải thiện CV từ AI."""
    category: str
    title: str
    action: str
    priority: int


class RawAnalysisResult(TypedDict):
    """Kết quả thô từ AI trước khi mapping sang Pydantic models."""
    skill_score: int
    structure_score: int
    content_score: int
    overall_score: int
    match_score: int | None
    missing_skills: list[str]
    recommendations: list[RecommendationDict]
    criteria_scores: dict[str, int]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_prompt(path: Path) -> str:
    """Đọc nội dung file prompt, raise FileNotFoundError nếu không tìm thấy."""
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_messages(cv_text: str, job_description: str | None, criteria: list[str]) -> tuple[str, list[dict]]:
    """
    Chọn prompt phù hợp, format với dữ liệu đầu vào, trả về
    (prompt_file_used, messages list) để gửi tới API.
    """
    if job_description:
        template = _load_prompt(_PROMPT_MATCH_JD)
        content = template.replace("{cv_text}", cv_text).replace("{job_description}", job_description)
    else:
        template = _load_prompt(_PROMPT_ANALYZE_CV)
        content = template.replace("{cv_text}", cv_text)

    # Nếu có tiêu chí, append thêm vào cuối prompt
    if criteria:
        criteria_block = "\n\n## EVALUATION CRITERIA\n"
        criteria_block += "The candidate must also be evaluated against these specific criteria. For each criterion, provide a score 0–100 in the `criteria_scores` object.\n\n"
        criteria_block += "\n".join(f"- {c}" for c in criteria)
        criteria_block += '\n\nAdd a `"criteria_scores"` field to your JSON output: an object where each key is the criterion name and the value is an integer 0–100.'
        content += criteria_block

    return content, [{"role": "user", "content": content}]


def _strip_markdown_fences(text: str) -> str:
    """Loại bỏ markdown code fences và extract phần JSON thuần túy."""
    text = text.strip()

    # Bỏ markdown code fences: ```json ... ``` hoặc ``` ... ```
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # bỏ dòng ``` hoặc ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Nếu vẫn còn text thừa trước { hoặc sau }, extract phần JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text.strip()


def _parse_raw_result(response_text: str) -> RawAnalysisResult:
    """
    Parse JSON từ response của AI thành RawAnalysisResult.
    Raise json.JSONDecodeError nếu không parse được.
    """
    cleaned = _strip_markdown_fences(response_text)
    data: dict = json.loads(cleaned)

    return RawAnalysisResult(
        skill_score=int(data["skill_score"]),
        structure_score=int(data["structure_score"]),
        content_score=int(data["content_score"]),
        overall_score=int(data["overall_score"]),
        match_score=int(data["match_score"]) if data.get("match_score") is not None else None,
        missing_skills=list(data.get("missing_skills", [])),
        criteria_scores={
            k: int(v) for k, v in data.get("criteria_scores", {}).items()
        },
        recommendations=[
            RecommendationDict(
                category=rec["category"],
                title=rec["title"],
                action=rec["action"],
                priority=int(rec["priority"]),
            )
            for rec in data.get("recommendations", [])
        ],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze(
    cv_text: str,
    job_description: str | None = None,
    criteria: list[str] | None = None,
) -> RawAnalysisResult:
    """
    Phân tích CV bằng DeepSeek AI.

    Args:
        cv_text:         Nội dung văn bản trích xuất từ CV.
        job_description: Mô tả công việc (tuỳ chọn). Nếu cung cấp sẽ dùng
                         prompt match_jd.txt và tính thêm match_score.

    Returns:
        RawAnalysisResult chứa điểm số, missing skills và recommendations.

    Raises:
        AnalysisError: Khi AI timeout, gặp lỗi API, hoặc JSON không hợp lệ
                       sau khi đã retry 1 lần.
    """
    _, messages = _build_messages(cv_text, job_description, criteria or [])

    client = openai.AsyncOpenAI(
        base_url="https://api.deepseek.com",
        api_key=settings.deepseek_api_key,
    )

    async def _call_api() -> str:
        """Gọi DeepSeek API và trả về nội dung text của response."""
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            timeout=30.0,
        )
        return response.choices[0].message.content or ""

    # --- Gọi API với retry 1 lần khi gặp JSONDecodeError ---
    response_text: str = ""
    for attempt in range(2):
        try:
            response_text = await _call_api()
        except openai.APITimeoutError as exc:
            raise AnalysisError(
                "DeepSeek API timeout sau 30 giây. Vui lòng thử lại."
            ) from exc
        except openai.APIError as exc:
            raise AnalysisError(
                f"DeepSeek API lỗi: {exc}"
            ) from exc

        logger.info("DeepSeek raw response: %r", response_text[:500])
        print(f"[DEBUG] DeepSeek raw response: {response_text[:500]!r}")

        try:
            return _parse_raw_result(response_text)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            if attempt == 0:
                logger.warning(
                    "Attempt %d: JSON parse thất bại (%s), đang retry...",
                    attempt + 1,
                    exc,
                )
                continue
            # attempt == 1 — đã retry, vẫn lỗi
            raise AnalysisError(
                f"Không thể parse JSON từ AI sau 2 lần thử. "
                f"Lỗi: {exc}. Response: {response_text[:200]!r}"
            ) from exc

    # Không bao giờ đến đây, nhưng để type checker hài lòng
    raise AnalysisError("Unexpected error in analyze()")
