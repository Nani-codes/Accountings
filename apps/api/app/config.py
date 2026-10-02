from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://workbench:workbench@localhost:5433/workbench"
    storage_backend: str = "local"  # local | s3
    local_storage_dir: str = "tmp/uploads"
    s3_endpoint: str = "http://localhost:9010"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio12345"
    s3_bucket: str = "workbench"
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

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
