from typing import Union
from botocore.config import Config

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class R2UploadError(Exception):
    """Raised when a local media file cannot be uploaded to Cloudflare R2."""


class R2DownloadError(Exception):
    """Raised when a remote media file cannot be downloaded from Cloudflare R2."""


def _env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _endpoint_url(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip("/")
    if not endpoint:
        return ""
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    return f"https://{endpoint}"


def _r2_settings() -> tuple[str, str, str, str]:
    endpoint = _endpoint_url(_env("CLOUDFLARE_R2_ENDPOINT", "CLOUDFLARE_ENDPOINT"))
    access_key = _env(
        "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_ACCESS_KEY_ID",
        "CLOUDFLARE_ACCESS_KEY",
    )
    secret_key = _env(
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_SECRET_ACCESS_KEY",
        "CLOUDFLARE_SECRET_KEY",
    )
    bucket = _env(
        "CLOUDFLARE_R2_BUCKET",
        "CLOUDFLARE_BUCKET",
        "CLOUDFLARE_BUCKET_NAME",
    )

    missing = []
    if not endpoint:
        missing.append("CLOUDFLARE_R2_ENDPOINT or CLOUDFLARE_ENDPOINT")
    if not access_key:
        missing.append(
            "CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_ACCESS_KEY_ID, "
            "or CLOUDFLARE_ACCESS_KEY"
        )
    if not secret_key:
        missing.append(
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY, CLOUDFLARE_SECRET_ACCESS_KEY, "
            "or CLOUDFLARE_SECRET_KEY"
        )
    if not bucket:
        missing.append(
            "CLOUDFLARE_R2_BUCKET, CLOUDFLARE_BUCKET, or CLOUDFLARE_BUCKET_NAME"
        )
    if missing:
        raise R2UploadError(f"Missing R2 setting(s): {', '.join(missing)}.")

    return endpoint, access_key, secret_key, bucket


def upload_media_file(local_path: Union[str, Path], user_id: str, filename: str) -> str:
    """Upload one local media file and return its R2 object key."""
    path = Path(local_path)
    if not path.exists():
        raise R2UploadError(f"Local media file does not exist: {path}")

    if not user_id:
        raise R2UploadError("Media file user_id is required for R2 object naming.")

    try:
        import boto3
    except ImportError as exc:
        raise R2UploadError(
            "boto3 is required for Cloudflare R2 uploads. Install requirements.txt."
        ) from exc

    endpoint, access_key, secret_key, bucket = _r2_settings()
    object_key = f"media/{user_id}/{filename}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    client.upload_file(str(path), bucket, object_key)
    return object_key


def download_media_file(
    local_path: Union[str, Path], user_id: str, filename: str
) -> str:
    """Download one R2 media object into the local media folder."""
    path = Path(local_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not user_id:
        raise R2DownloadError("Media file user_id is required for R2 object naming.")

    try:
        import boto3
    except ImportError as exc:
        raise R2DownloadError(
            "boto3 is required for Cloudflare R2 downloads. Install requirements.txt."
        ) from exc

    endpoint, access_key, secret_key, bucket = _r2_settings()
    object_key = f"media/{user_id}/{filename}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    client.download_file(bucket, object_key, str(path))
    return object_key
