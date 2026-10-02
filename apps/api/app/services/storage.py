from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import Config

from app.config import settings


def _local_root() -> Path:
    root = Path(settings.local_storage_dir)
    if not root.is_absolute():
        # apps/api cwd when running uvicorn
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    if settings.storage_backend == "local":
        _local_root()
        return
    client = _client()
    buckets = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if settings.s3_bucket not in buckets:
        client.create_bucket(Bucket=settings.s3_bucket)


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    ensure_bucket()
    if settings.storage_backend == "local":
        path = _local_root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key
    _client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def get_object_bytes(key: str) -> bytes:
    if settings.storage_backend == "local":
        path = _local_root() / key
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()
    obj = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    return obj["Body"].read()
