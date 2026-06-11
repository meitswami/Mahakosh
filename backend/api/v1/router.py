from fastapi import APIRouter

from backend.api.v1.routes import (
    accounting,
    admin,
    agents,
    audit,
    auth,
    cfo,
    channels,
    chat,
    documents,
    gst,
    intelligence,
    knowledge,
    licenses,
    ocr,
    platform,
    reports,
    subscriptions,
    tenants,
    usage,
    workflows,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(cfo.router, prefix="/cfo", tags=["cfo"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_v1_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_v1_router.include_router(accounting.router, prefix="/accounting", tags=["accounting"])
api_v1_router.include_router(gst.router, prefix="/gst", tags=["gst"])
api_v1_router.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
api_v1_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_v1_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_v1_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_v1_router.include_router(licenses.router, prefix="/licenses", tags=["licenses"])
api_v1_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_v1_router.include_router(platform.router, prefix="/platform", tags=["platform"])
