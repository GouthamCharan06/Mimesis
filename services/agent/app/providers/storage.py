"""Google Cloud Storage provider for media asset management."""

from __future__ import annotations

from google.cloud import storage

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.retry import with_provider_retry
from app.domain.models import MediaType
from app.providers.interfaces import StorageService

logger = get_logger(__name__)

MEDIA_TYPE_CONTENT_TYPES: dict[MediaType, str] = {
    MediaType.IMAGE: "image/png",
    MediaType.AUDIO: "audio/wav",
    MediaType.MUSIC: "audio/wav",
    MediaType.VIDEO: "video/mp4",
    MediaType.SUBTITLE: "text/vtt",
}


class GCSStorageProvider(StorageService):
    """Google Cloud Storage implementation for media assets."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = storage.Client(project=settings.google_cloud_project or None)
        self._bucket_name = settings.gcs_media_bucket
        logger.info("gcs_storage_initialized", bucket=self._bucket_name)

    @property
    def _bucket(self) -> storage.Bucket:
        return self._client.bucket(self._bucket_name)

    @with_provider_retry()
    async def upload_asset(
        self,
        data: bytes,
        filename: str,
        media_type: MediaType,
        *,
        metadata: dict[str, str] | None = None,
    ) -> str:
        content_type = MEDIA_TYPE_CONTENT_TYPES.get(media_type, "application/octet-stream")
        blob = self._bucket.blob(f"assets/{filename}")
        blob.upload_from_string(data, content_type=content_type)
        if metadata:
            blob.metadata = metadata
            blob.patch()
        storage_url = f"gs://{self._bucket_name}/assets/{filename}"
        logger.info("asset_uploaded", filename=filename, url=storage_url)
        return storage_url

    @with_provider_retry()
    async def get_asset_url(self, storage_path: str) -> str:
        blob_path = storage_path.replace(f"gs://{self._bucket_name}/", "")
        blob = self._bucket.blob(blob_path)
        url = blob.generate_signed_url(expiration=3600)
        return url

    @with_provider_retry()
    async def download_asset(self, storage_path: str) -> bytes:
        blob_path = storage_path.replace(f"gs://{self._bucket_name}/", "")
        blob = self._bucket.blob(blob_path)
        return blob.download_as_bytes()
