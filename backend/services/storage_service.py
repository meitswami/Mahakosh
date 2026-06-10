import hashlib
import os
from io import BytesIO
from pathlib import Path
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from backend.core.config import settings


class StorageService:
    """Object storage service using MinIO with local filesystem fallback."""

    def __init__(self) -> None:
        self.bucket = settings.MINIO_BUCKET
        self.local_fallback = Path("storage/uploads")
        self.local_fallback.mkdir(parents=True, exist_ok=True)
        self._client: Minio | None = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL,
            )
            self._ensure_bucket()
        return self._client

    def _ensure_bucket(self) -> None:
        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
        except S3Error:
            pass

    def upload_file(
        self,
        tenant_id: UUID,
        file_name: str,
        data: bytes,
        content_type: str,
    ) -> tuple[str, str]:
        object_key = f"{tenant_id}/{self._hash_prefix(data)}/{file_name}"
        checksum = hashlib.sha256(data).hexdigest()

        try:
            self.client.put_object(
                self.bucket,
                object_key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return f"minio://{self.bucket}/{object_key}", checksum
        except Exception:
            local_path = self.local_fallback / tenant_id.hex / file_name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
            return str(local_path.resolve()), checksum

    def download_to_path(self, storage_path: str, dest_path: str) -> str:
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

        if storage_path.startswith("minio://"):
            parts = storage_path.replace("minio://", "").split("/", 1)
            bucket = parts[0]
            object_key = parts[1] if len(parts) > 1 else ""
            self.client.fget_object(bucket, object_key, dest_path)
            return dest_path

        if os.path.exists(storage_path):
            import shutil
            shutil.copy2(storage_path, dest_path)
            return dest_path

        raise FileNotFoundError(f"Storage path not found: {storage_path}")

    def get_local_copy(self, storage_path: str, work_dir: str) -> str:
        file_name = Path(storage_path).name
        dest = str(Path(work_dir) / file_name)
        return self.download_to_path(storage_path, dest)

    @staticmethod
    def _hash_prefix(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:16]


storage_service = StorageService()
