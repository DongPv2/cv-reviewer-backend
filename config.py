from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # DeepSeek AI API key
    deepseek_api_key: str = ""

    # Session TTL in minutes (default: 60)
    session_ttl_minutes: int = 60

    # Maximum file size in MB (default: 10)
    max_file_size_mb: int = 10

    # Maximum Job Description length in characters (default: 5000)
    max_jd_length: int = 5000

    # Allowed CORS origins (comma-separated string or list)
    allowed_origins: str = "http://localhost:5173"

    # Backend server port (default: 8000)
    port: int = 8000

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed_origins into a list of origin strings."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
