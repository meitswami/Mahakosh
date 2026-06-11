from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole
from backend.intelligence.service import IntelligenceService
from backend.models.analytics import AnalyticsReport, ScheduledReport
from backend.schemas.intelligence import (
    NLQueryRequest,
    NLQueryResponse,
    ReportGenerateRequest,
    ScheduledReportRequest,
)

router = APIRouter()


def _service(db: AsyncSession) -> IntelligenceService:
    return IntelligenceService(db)


@router.get("/executive")
async def executive_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=7, le=365),
) -> dict[str, Any]:
    return await _service(db).get_executive(current_user.tenant_id, days)


@router.get("/financial")
async def financial_intelligence(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await _service(db).get_financial(current_user.tenant_id)


@router.get("/gst")
async def gst_intelligence(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await _service(db).get_gst(current_user.tenant_id)


@router.get("/vendors")
async def vendor_intelligence(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await _service(db).get_vendors(current_user.tenant_id)


@router.get("/customers")
async def customer_intelligence(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await _service(db).get_customers(current_user.tenant_id)


@router.get("/inventory")
async def inventory_intelligence(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await _service(db).get_inventory(current_user.tenant_id)


@router.get("/workflows")
async def workflow_intelligence(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=7, le=365),
) -> dict[str, Any]:
    return await _service(db).get_workflows(current_user.tenant_id, days)


@router.get("/insights")
async def ai_insights(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=7, le=365),
) -> dict[str, Any]:
    return await _service(db).get_insights(current_user.tenant_id, days)


@router.post("/query", response_model=NLQueryResponse)
async def natural_language_query(
    request: NLQueryRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NLQueryResponse:
    result = await _service(db).query(current_user.tenant_id, request.question, request.days)
    await db.commit()
    return NLQueryResponse(**result)


@router.get("/forecasts")
async def forecasts(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await _service(db).get_forecasts(current_user.tenant_id)


@router.get("/anomalies")
async def anomalies(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await _service(db).get_anomalies(current_user.tenant_id)


@router.get("/dashboard/{dashboard_type}")
async def get_dashboard(
    dashboard_type: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=7, le=365),
) -> dict[str, Any]:
    try:
        return await _service(db).get_dashboard(dashboard_type, current_user.tenant_id, days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reports/generate")
async def generate_report_download(
    request: ReportGenerateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = _service(db)
    try:
        content, media_type, filename = await svc.generate_report(
            current_user.tenant_id,
            request.report_type,
            request.format,
            request.parameters.get("days", 30),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report = AnalyticsReport(
        tenant_id=current_user.tenant_id,
        name=request.name,
        report_type=request.report_type,
        format=request.format,
        status="completed",
        parameters=request.parameters,
        result_size_bytes=len(content),
        created_by=current_user.id,
        completed_at=datetime.now(UTC),
    )
    db.add(report)
    await db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports")
async def list_analytics_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    result = await db.execute(
        select(AnalyticsReport)
        .where(AnalyticsReport.tenant_id == current_user.tenant_id)
        .order_by(AnalyticsReport.created_at.desc())
        .limit(50)
    )
    reports = result.scalars().all()
    return {
        "reports": [
            {
                "id": str(r.id),
                "name": r.name,
                "report_type": r.report_type,
                "format": r.format,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in reports
        ],
        "total": len(reports),
    }


@router.get("/reports/templates")
async def report_templates() -> dict[str, Any]:
    return {
        "templates": [
            {"type": "gst_summary", "name": "GST Summary Report", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "vendor_ledger", "name": "Vendor Ledger", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "purchase_register", "name": "Purchase Register", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "sales_register", "name": "Sales Register", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "executive_summary", "name": "Executive Summary", "formats": ["excel", "pdf", "word"]},
            {"type": "financial_summary", "name": "Financial Summary", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "workflow_report", "name": "Workflow Performance", "formats": ["excel", "csv"]},
        ],
        "schedules": ["daily", "weekly", "monthly", "quarterly", "yearly"],
    }


@router.post("/reports/schedule", status_code=201)
async def schedule_report(
    request: ScheduledReportRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    valid_schedules = {"daily", "weekly", "monthly", "quarterly", "yearly"}
    if request.schedule not in valid_schedules:
        raise HTTPException(status_code=400, detail=f"Invalid schedule. Use: {valid_schedules}")

    next_run = _compute_next_run(request.schedule)
    scheduled = ScheduledReport(
        tenant_id=current_user.tenant_id,
        name=request.name,
        report_type=request.report_type,
        format=request.format,
        schedule=request.schedule,
        parameters=request.parameters,
        recipients=request.recipients,
        created_by=current_user.id,
        next_run_at=next_run,
    )
    db.add(scheduled)
    await db.flush()
    return {"id": str(scheduled.id), "next_run_at": next_run.isoformat()}


@router.get("/reports/scheduled")
async def list_scheduled_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.tenant_id == current_user.tenant_id,
            ScheduledReport.is_active.is_(True),
        )
    )
    items = result.scalars().all()
    return {
        "scheduled": [
            {
                "id": str(s.id),
                "name": s.name,
                "report_type": s.report_type,
                "schedule": s.schedule,
                "format": s.format,
                "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            }
            for s in items
        ]
    }


def _compute_next_run(schedule: str) -> datetime:
    now = datetime.now(UTC)
    deltas = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
        "quarterly": timedelta(days=90),
        "yearly": timedelta(days=365),
    }
    return now + deltas.get(schedule, timedelta(days=30))
