import mimetypes
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.channels.base.types import AttachmentType, ChannelAttachment
from backend.core.config import settings

logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf": AttachmentType.PDF,
    ".png": AttachmentType.IMAGE,
    ".jpg": AttachmentType.IMAGE,
    ".jpeg": AttachmentType.IMAGE,
    ".webp": AttachmentType.IMAGE,
    ".xlsx": AttachmentType.EXCEL,
    ".xls": AttachmentType.EXCEL,
    ".csv": AttachmentType.CSV,
    ".zip": AttachmentType.ZIP,
    ".docx": AttachmentType.WORD,
    ".doc": AttachmentType.WORD,
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


class ChannelFileProcessor:
    """Process channel file uploads — store in MinIO and trigger OCR workflows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process(
        self,
        attachment: ChannelAttachment,
        file_bytes: bytes,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict:
        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit")

        ext = "." + attachment.filename.rsplit(".", 1)[-1].lower() if "." in attachment.filename else ""
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type {ext} not allowed")

        storage_path = await self._store_file(tenant_id, attachment.filename, file_bytes, attachment.content_type)
        attachment.storage_path = storage_path

        workflow_result = None
        if attachment.attachment_type in (AttachmentType.PDF, AttachmentType.IMAGE):
            workflow_result = await self._trigger_ocr_workflow(
                tenant_id, user_id, storage_path, attachment.filename
            )

        return {
            "storage_path": storage_path,
            "attachment_type": attachment.attachment_type.value,
            "size_bytes": len(file_bytes),
            "workflow": workflow_result,
        }

    async def _store_file(
        self,
        tenant_id: UUID,
        filename: str,
        data: bytes,
        content_type: str,
    ) -> str:
        object_name = f"channels/{tenant_id}/{uuid4()}_{filename}"
        try:
            from minio import Minio

            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL,
            )
            from io import BytesIO
            client.put_object(
                settings.MINIO_BUCKET,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            )
            return object_name
        except Exception as exc:
            logger.warning("minio_store_failed", error=str(exc))
            return f"local://{object_name}"

    async def _trigger_ocr_workflow(
        self,
        tenant_id: UUID,
        user_id: UUID,
        storage_path: str,
        filename: str,
    ) -> dict | None:
        try:
            from backend.workflows.workflow_engine import WorkflowEngine

            engine = WorkflowEngine(self.db)
            wf = await engine.create_workflow_record(
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_type="document_processing",
                name=f"Channel Upload: {filename}",
                input_data={"storage_path": storage_path, "filename": filename, "source": "channel"},
            )
            return {"workflow_id": str(wf.id), "status": "created"}
        except Exception as exc:
            logger.error("channel_ocr_workflow_failed", error=str(exc))
            return None
