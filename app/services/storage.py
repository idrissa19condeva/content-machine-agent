import boto3
from botocore.config import Config as BotoConfig
from app.config import get_settings

settings = get_settings()

_client = None


def _get_s3_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=BotoConfig(signature_version="s3v4"),
        )
        # Créer le bucket si inexistant
        try:
            _client.head_bucket(Bucket=settings.s3_bucket)
        except Exception:
            _client.create_bucket(Bucket=settings.s3_bucket)
    return _client


async def upload_file(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    """Upload un fichier vers S3/MinIO et retourne l'URL."""
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"{settings.s3_endpoint}/{settings.s3_bucket}/{key}"


async def download_file(key: str) -> bytes:
    """Télécharge un fichier depuis S3/MinIO."""
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Génère une URL présignée pour accès temporaire."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


async def delete_file(key: str) -> None:
    client = _get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket, Key=key)
