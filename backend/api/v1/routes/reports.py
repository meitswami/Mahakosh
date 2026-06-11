"""Reports API — delegates to intelligence reporting engine."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import CurrentUser, get_current_user, require_role
from backend.core.security import UserRole
from backend.intelligence.service import IntelligenceService
from backend.models.analytics import AnalyticsReport, ScheduledReport
from backend.schemas.intelligence import ReportGenerateRequest, ScheduledReportRequest

router = APIRouter()


@router.get("")
async def list_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
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
            }
            for r in reports
        ],
        "total": len(reports),
    }


@router.post("/generate")
async def generate_report(
    definition: ReportGenerateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ACCOUNTANT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = IntelligenceService(db)
    try:
        content, media_type, filename = await svc.generate_report(
            current_user.tenant_id,
            definition.report_type,
            definition.format,
            definition.parameters.get("days", 30),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report = AnalyticsReport(
        tenant_id=current_user.tenant_id,
        name=definition.name,
        report_type=definition.report_type,
        format=definition.format,
        status="completed",
        parameters=definition.parameters,
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


@router.get("/templates")
async def list_report_templates() -> dict:
    return {
        "templates": [
            {"type": "gst_summary", "name": "GST Summary Report", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "vendor_ledger", "name": "Vendor Ledger", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "purchase_register", "name": "Purchase Register", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "sales_register", "name": "Sales Register", "formats": ["excel", "csv", "pdf", "word"]},
            {"type": "executive_summary", "name": "Executive Summary", "formats": ["excel", "pdf", "word"]},
            {"type": "financial_summary", "name": "Financial Summary", "formats": ["excel", "csv", "pdf", "word"]},
        ],
        "schedules": ["daily", "weekly", "monthly", "quarterly", "yearly"],
    }


@router.post("/schedule", status_code=201)
async def create_scheduled_report(
    request: ScheduledReportRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    valid = {"daily", "weekly", "monthly", "quarterly", "yearly"}
    if request.schedule not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {valid}")

    deltas = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
        "quarterly": timedelta(days=90),
        "yearly": timedelta(days=365),
    }
    next_run = datetime.now(UTC) + deltas[request.schedule]

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
