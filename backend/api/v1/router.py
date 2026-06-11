from fastapi import APIRouter

from backend.api.v1.routes import (
    accounting,
    admin,
    agents,
    audit,
    auth,
    channels,
    chat,
    documents,
    gst,
    knowledge,
    ocr,
    reports,
    workflows,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_v1_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_v1_router.include_router(accounting.router, prefix="/accounting", tags=["accounting"])
api_v1_router.include_router(gst.router, prefix="/gst", tags=["gst"])
api_v1_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_v1_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
