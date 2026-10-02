from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://workbench:workbench@localhost:5432/workbench"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio12345"
    s3_bucket: str = "workbench"
    openai_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str = "dev-change-me"
    api_cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
