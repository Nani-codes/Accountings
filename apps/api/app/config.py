from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://workbench:workbench@localhost:5433/workbench"

    # Storage: local disk | S3-compatible (MinIO) | real AWS S3
    storage_backend: str = "local"  # local | s3
    local_storage_dir: str = "tmp/uploads"
    # Empty / unset endpoint => real AWS S3. Set for MinIO / LocalStack.
    s3_endpoint: str = ""
    s3_access_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "S3_ACCESS_KEY",
            "AWS_ACCESS_KEY_ID",
        ),
    )
    s3_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "S3_SECRET_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_ACCESS_SECRET",
        ),
    )
    s3_bucket: str = Field(
        default="workbench",
        validation_alias=AliasChoices("S3_BUCKET", "AWS_BUCKET_NAME"),
    )
    s3_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("S3_REGION", "AWS_REGION"),
    )
    # Auth
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str = "dev-change-me"
    api_cors_origins: str = "http://localhost:3000"
    # Vertex AI (Gemini via Agno)
    google_genai_use_vertexai: bool = True
    google_cloud_project: str = "purplegrid"
    google_cloud_location: str = "us-central1"
    google_application_credentials: str = ""
    vertex_model_id: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    # TallyPrime hosted connector (dial-out from firm PC)
    tally_token_pepper: str = "dev-tally-pepper-change-me"
    tally_connector_download_url: str = ""  # optional; UI can show coming soon if empty
    tally_heartbeat_stale_seconds: int = 60
    tally_rpc_timeout_seconds: float = 25.0

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("storage_backend")
    @classmethod
    def _normalize_backend(cls, v: str) -> str:
        value = (v or "local").strip().lower()
        if value not in {"local", "s3"}:
            raise ValueError("storage_backend must be 'local' or 's3'")
        return value

    @property
    def s3_uses_custom_endpoint(self) -> bool:
        return bool((self.s3_endpoint or "").strip())


settings = Settings()
