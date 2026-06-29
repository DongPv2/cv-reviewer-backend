from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class OverallClassification(str, Enum):
    """Phân loại điểm tổng thể dựa trên Overall_Score."""
    NEEDS_MAJOR_IMPROVEMENT = "Cần cải thiện đáng kể"  # 0–49
    NEEDS_IMPROVEMENT = "Cần cải thiện"                 # 50–69
    GOOD = "Khá tốt"                                    # 70–84
    EXCELLENT = "Xuất sắc"                              # 85–100


class MatchClassification(str, Enum):
    """Phân loại mức độ phù hợp với Job Description."""
    LOW = "Thấp"           # 0–39
    MEDIUM = "Trung bình"  # 40–69
    HIGH = "Cao"           # 70–100


class RecommendationCategory(str, Enum):
    """Danh mục của từng đề xuất cải thiện CV."""
    SKILLS = "Kỹ năng"
    STRUCTURE = "Cấu trúc"
    CONTENT = "Nội dung"
    JOB_FIT = "Phù hợp với công việc"


class Recommendation(BaseModel):
    """Một đề xuất cải thiện CV cụ thể."""
    category: RecommendationCategory
    priority: int = Field(..., ge=1, description="Mức độ ưu tiên, 1 là cao nhất")
    title: str = Field(..., description="Tiêu đề ngắn gọn của đề xuất")
    action: str = Field(..., description="Hành động cụ thể người dùng cần thực hiện")


class Scores(BaseModel):
    """Điểm số phân tích CV theo các tiêu chí."""
    skill_score: Optional[int] = Field(None, ge=0, le=100, description="Điểm kỹ năng (0–100)")
    structure_score: Optional[int] = Field(None, ge=0, le=100, description="Điểm cấu trúc (0–100)")
    content_score: Optional[int] = Field(None, ge=0, le=100, description="Điểm nội dung (0–100)")
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="Điểm tổng thể (0–100)")
    match_score: Optional[int] = Field(None, ge=0, le=100, description="Điểm phù hợp với JD (0–100), None nếu không có JD")
    overall_classification: Optional[OverallClassification] = Field(
        None, description="Phân loại tổng thể dựa trên overall_score"
    )
    match_classification: Optional[MatchClassification] = Field(
        None, description="Phân loại mức độ phù hợp, None nếu không có JD"
    )


class AnalysisReport(BaseModel):
    """Báo cáo phân tích CV đầy đủ."""
    scores: Scores
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Kỹ năng có trong JD nhưng thiếu trong CV"
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Danh sách đề xuất cải thiện CV, tối đa 10 items"
    )
    has_job_description: bool = Field(
        False,
        description="True nếu phân tích có kèm theo Job Description"
    )
    criteria_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Điểm theo từng tiêu chí tuyển chọn (0–100)"
    )
    criteria: list[str] = Field(
        default_factory=list,
        description="Danh sách tiêu chí đã dùng để đánh giá"
    )


class CVSession(BaseModel):
    """Phiên làm việc của người dùng lưu trữ CV và kết quả phân tích."""
    session_id: str = Field(..., description="UUID v4 định danh phiên")
    file_name: str = Field(..., description="Tên file CV đã upload")
    extracted_text: str = Field(..., description="Nội dung văn bản trích xuất từ CV")
    job_description: Optional[str] = Field(None, description="Mô tả công việc do người dùng cung cấp")
    criteria: list[str] = Field(default_factory=list, description="Danh sách tiêu chí tuyển chọn")
    report: Optional[AnalysisReport] = Field(None, description="Kết quả phân tích, None khi chưa hoàn thành")
    created_at: datetime = Field(..., description="Thời điểm tạo phiên")
    last_active: datetime = Field(..., description="Thời điểm request cuối cùng")
    status: str = Field(
        ...,
        description="Trạng thái phiên: 'pending' | 'analyzing' | 'complete' | 'error'"
    )
    error: Optional[str] = Field(None, description="Thông báo lỗi nếu status là 'error'")


class AnalyzeRequest(BaseModel):
    """Request body cho endpoint phân tích CV."""
    job_description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Mô tả công việc để đối chiếu với CV (tùy chọn, tối đa 5000 ký tự)"
    )
