"""Business dummy data — users, masters, documents, vouchers, workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import UserRole, hash_password
from backend.models.approval import ApprovalQueue
from backend.models.audit import AuditLog
from backend.models.customer import Customer
from backend.models.document import Document, DocumentStatus, DocumentType
from backend.models.item import Item
from backend.models.ledger import Ledger
from backend.models.role import Role
from backend.models.user import User
from backend.models.vendor import Vendor
from backend.models.voucher import VoucherDraft, VoucherLine
from backend.models.workflow import Workflow, WorkflowState, WorkflowStep

DEFAULT_PASSWORD = "Mahakosh@2026"

# Extra users per tenant slug (beyond the admin created at provision time)
EXTRA_USERS: dict[str, list[dict]] = {
    "demo-sme": [
        {"email": "manager@acme.demo.mahakosh.in", "full_name": "Ravi Mehta", "role": UserRole.MANAGER},
        {"email": "accountant@acme.demo.mahakosh.in", "full_name": "Sneha Desai", "role": UserRole.ACCOUNTANT},
        {"email": "viewer@acme.demo.mahakosh.in", "full_name": "Karan Joshi", "role": UserRole.VIEWER},
    ],
    "demo-enterprise": [
        {"email": "manager@horizon.demo.mahakosh.in", "full_name": "Arjun Singh", "role": UserRole.MANAGER},
        {"email": "accountant@horizon.demo.mahakosh.in", "full_name": "Divya Rao", "role": UserRole.ACCOUNTANT},
        {"email": "auditor@horizon.demo.mahakosh.in", "full_name": "Meera Iyer", "role": UserRole.AUDITOR},
    ],
    "demo-ca": [
        {"email": "staff@sharma-ca.demo.mahakosh.in", "full_name": "Pooja Gupta", "role": UserRole.ACCOUNTANT},
        {"email": "manager@sharma-ca.demo.mahakosh.in", "full_name": "Rohit Verma", "role": UserRole.MANAGER},
    ],
    "demo-partner": [
        {"email": "ops@finadvisors.demo.mahakosh.in", "full_name": "Anita Kulkarni", "role": UserRole.MANAGER},
    ],
    "client-alpha": [
        {"email": "finance@alpha.demo.mahakosh.in", "full_name": "Alpha Finance", "role": UserRole.ACCOUNTANT},
    ],
}

VENDORS = [
    {"name": "Reliance Industries Ltd", "gstin": "27AAACR5055K1Z7", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Tata Steel Ltd", "gstin": "20AAACT2727Q1ZW", "city": "Jamshedpur", "state": "Jharkhand"},
    {"name": "Infosys Technologies", "gstin": "29AAACI1681G1ZN", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "Local Stationery Mart", "gstin": "27AABCL1234A1Z5", "city": "Pune", "state": "Maharashtra"},
]

CUSTOMERS = [
    {"name": "Metro Retail Chain", "gstin": "27AABCM1234E1Z2", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Green Farms Cooperative", "gstin": "24AABCG5678F1Z3", "city": "Ahmedabad", "state": "Gujarat"},
    {"name": "TechStart Solutions", "gstin": "29AABCT9012G1Z4", "city": "Bengaluru", "state": "Karnataka"},
]

ITEMS = [
    {"name": "Cotton Fabric Roll", "sku": "CFR-001", "hsn_code": "5208", "unit": "MTR", "default_rate": Decimal("450.00"), "gst_rate": Decimal("12.00")},
    {"name": "Polyester Yarn", "sku": "PYR-002", "hsn_code": "5402", "unit": "KG", "default_rate": Decimal("280.00"), "gst_rate": Decimal("12.00")},
    {"name": "Industrial Dye", "sku": "IDY-003", "hsn_code": "3204", "unit": "LTR", "default_rate": Decimal("1200.00"), "gst_rate": Decimal("18.00")},
    {"name": "Packaging Carton", "sku": "PKG-004", "hsn_code": "4819", "unit": "NOS", "default_rate": Decimal("35.00"), "gst_rate": Decimal("18.00")},
]

LEDGERS = [
    {"name": "Purchase Account", "ledger_type": "expense", "parent_group": "Purchase Accounts", "opening_balance": Decimal("0")},
    {"name": "Sales Account", "ledger_type": "income", "parent_group": "Sales Accounts", "opening_balance": Decimal("0")},
    {"name": "CGST Payable", "ledger_type": "liability", "parent_group": "Duties & Taxes", "opening_balance": Decimal("12500.00")},
    {"name": "SGST Payable", "ledger_type": "liability", "parent_group": "Duties & Taxes", "opening_balance": Decimal("12500.00")},
    {"name": "HDFC Bank Current A/c", "ledger_type": "asset", "parent_group": "Bank Accounts", "opening_balance": Decimal("850000.00")},
    {"name": "Cash in Hand", "ledger_type": "asset", "parent_group": "Cash-in-Hand", "opening_balance": Decimal("25000.00")},
]

DOCUMENTS = [
    {"title": "Purchase Invoice #PI-2026-0142", "document_type": DocumentType.INVOICE, "file_name": "pi-2026-0142.pdf", "status": DocumentStatus.PROCESSED},
    {"title": "Sales Invoice #SI-2026-0089", "document_type": DocumentType.INVOICE, "file_name": "si-2026-0089.pdf", "status": DocumentStatus.PROCESSED},
    {"title": "Bank Statement March 2026", "document_type": DocumentType.BANK_STATEMENT, "file_name": "hdfc-mar-2026.pdf", "status": DocumentStatus.PROCESSED},
    {"title": "GST GSTR-1 Draft", "document_type": DocumentType.GST_RETURN, "file_name": "gstr1-mar-2026.pdf", "status": DocumentStatus.UPLOADED},
    {"title": "Vendor Credit Note #CN-445", "document_type": DocumentType.CREDIT_NOTE, "file_name": "cn-445.pdf", "status": DocumentStatus.PROCESSING},
]

# Tenants that receive full business dummy data
BUSINESS_DATA_TENANTS = ("demo-sme", "demo-enterprise", "demo-ca", "client-alpha")


async def _has_business_data(db: AsyncSession, tenant_id: UUID) -> bool:
    count = (await db.execute(
        select(func.count()).select_from(Vendor).where(Vendor.tenant_id == tenant_id)
    )).scalar() or 0
    return count > 0


async def _get_roles(db: AsyncSession, tenant_id: UUID) -> dict[str, Role]:
    result = await db.execute(select(Role).where(Role.tenant_id == tenant_id))
    return {r.name: r for r in result.scalars().all()}


async def _get_admin_user(db: AsyncSession, tenant_id: UUID) -> User | None:
    roles = await _get_roles(db, tenant_id)
    admin_role = roles.get(UserRole.ADMIN)
    if not admin_role:
        return None
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.role_id == admin_role.id).limit(1)
    )
    return result.scalar_one_or_none()


async def seed_extra_users(
    db: AsyncSession,
    tenant_id: UUID,
    tenant_slug: str,
    credentials: list[dict],
) -> list[dict]:
    if tenant_slug not in EXTRA_USERS:
        return []
    roles = await _get_roles(db, tenant_id)
    admin = await _get_admin_user(db, tenant_id)
    created_users: list[dict] = []

    for spec in EXTRA_USERS[tenant_slug]:
        existing = await db.execute(
            select(User).where(User.tenant_id == tenant_id, User.email == spec["email"])
        )
        if existing.scalar_one_or_none():
            credentials.append({
                "tenant_slug": tenant_slug,
                "email": spec["email"],
                "password": DEFAULT_PASSWORD,
                "role": spec["role"],
                "full_name": spec["full_name"],
            })
            continue

        role = roles.get(spec["role"])
        if not role:
            continue

        user = User(
            tenant_id=tenant_id,
            email=spec["email"],
            hashed_password=hash_password(DEFAULT_PASSWORD),
            full_name=spec["full_name"],
            role_id=role.id,
            is_verified=True,
            is_active=True,
            created_by=admin.id if admin else None,
        )
        db.add(user)
        await db.flush()
        created_users.append(spec)
        credentials.append({
            "tenant_slug": tenant_slug,
            "email": spec["email"],
            "password": DEFAULT_PASSWORD,
            "role": spec["role"],
            "full_name": spec["full_name"],
        })

    return created_users


async def seed_business_masters(
    db: AsyncSession,
    tenant_id: UUID,
    admin_user_id: UUID,
) -> dict:
    vendors: list[Vendor] = []
    for v in VENDORS:
        vendors.append(Vendor(tenant_id=tenant_id, **v, email=f"accounts@{v['name'].split()[0].lower()}.in"))
    db.add_all(vendors)

    customers: list[Customer] = []
    for c in CUSTOMERS:
        customers.append(Customer(tenant_id=tenant_id, **c, email=f"billing@{c['name'].split()[0].lower()}.in"))
    db.add_all(customers)

    items: list[Item] = []
    for i in ITEMS:
        items.append(Item(tenant_id=tenant_id, **i, category="Raw Materials"))
    db.add_all(items)

    ledgers: list[Ledger] = []
    for lg in LEDGERS:
        ledgers.append(Ledger(
            tenant_id=tenant_id,
            name=lg["name"],
            ledger_type=lg["ledger_type"],
            parent_group=lg["parent_group"],
            opening_balance=lg["opening_balance"],
            current_balance=lg["opening_balance"],
            tally_ledger_name=lg["name"],
        ))
    db.add_all(ledgers)
    await db.flush()

    return {"vendors": vendors, "customers": customers, "items": items, "ledgers": ledgers}


async def seed_documents(
    db: AsyncSession,
    tenant_id: UUID,
    admin_user_id: UUID,
) -> list[Document]:
    docs: list[Document] = []
    for i, d in enumerate(DOCUMENTS):
        docs.append(Document(
            tenant_id=tenant_id,
            title=d["title"],
            document_type=d["document_type"],
            status=d["status"],
            file_name=d["file_name"],
            file_path=f"{tenant_id}/documents/{d['file_name']}",
            file_size=102400 + i * 5000,
            mime_type="application/pdf",
            checksum=f"seed-checksum-{i:04d}",
            uploaded_by=admin_user_id,
            processed_at=datetime.now(UTC) if d["status"] == DocumentStatus.PROCESSED else None,
            metadata_={"seed": True, "source": "seed_business_data"},
        ))
    db.add_all(docs)
    await db.flush()
    return docs


async def seed_vouchers(
    db: AsyncSession,
    tenant_id: UUID,
    admin_user_id: UUID,
    masters: dict,
) -> list[VoucherDraft]:
    vendors: list[Vendor] = masters["vendors"]
    items: list[Item] = masters["items"]
    ledgers: list[Ledger] = masters["ledgers"]
    purchase_ledger = next((l for l in ledgers if l.name == "Purchase Account"), ledgers[0])

    vouchers: list[VoucherDraft] = []
    specs = [
        {
            "voucher_type": "purchase",
            "voucher_number": "PV-2026-0312",
            "party_name": vendors[0].name,
            "vendor_id": vendors[0].id,
            "subtotal": Decimal("45000.00"),
            "cgst": Decimal("2700.00"),
            "sgst": Decimal("2700.00"),
            "total": Decimal("50400.00"),
            "status": "approved",
            "approval_status": "approved",
        },
        {
            "voucher_type": "sales",
            "voucher_number": "SV-2026-0089",
            "party_name": masters["customers"][0].name,
            "customer_id": masters["customers"][0].id,
            "subtotal": Decimal("125000.00"),
            "cgst": Decimal("7500.00"),
            "sgst": Decimal("7500.00"),
            "total": Decimal("140000.00"),
            "status": "draft",
            "approval_status": "pending",
        },
        {
            "voucher_type": "purchase",
            "voucher_number": "PV-2026-0315",
            "party_name": vendors[2].name,
            "vendor_id": vendors[2].id,
            "subtotal": Decimal("18000.00"),
            "cgst": Decimal("1620.00"),
            "sgst": Decimal("1620.00"),
            "total": Decimal("21240.00"),
            "status": "draft",
            "approval_status": "pending",
        },
    ]

    for spec in specs:
        voucher = VoucherDraft(
            tenant_id=tenant_id,
            voucher_type=spec["voucher_type"],
            voucher_number=spec["voucher_number"],
            voucher_date=date.today() - timedelta(days=3),
            party_name=spec["party_name"],
            vendor_id=spec.get("vendor_id"),
            customer_id=spec.get("customer_id"),
            subtotal=spec["subtotal"],
            cgst_amount=spec["cgst"],
            sgst_amount=spec["sgst"],
            igst_amount=Decimal("0"),
            total_amount=spec["total"],
            status=spec["status"],
            approval_status=spec["approval_status"],
            narration=f"Seed voucher {spec['voucher_number']}",
            created_by=admin_user_id,
        )
        db.add(voucher)
        await db.flush()

        line_item = items[0]
        db.add(VoucherLine(
            tenant_id=tenant_id,
            voucher_id=voucher.id,
            line_number=1,
            item_id=line_item.id,
            description=line_item.name,
            hsn_code=line_item.hsn_code,
            quantity=Decimal("100"),
            unit=line_item.unit,
            rate=line_item.default_rate or Decimal("100"),
            amount=spec["subtotal"],
            gst_rate=line_item.gst_rate,
            cgst_amount=spec["cgst"],
            sgst_amount=spec["sgst"],
            ledger_id=purchase_ledger.id,
        ))
        vouchers.append(voucher)

    await db.flush()
    return vouchers


async def seed_workflows(
    db: AsyncSession,
    tenant_id: UUID,
    admin_user_id: UUID,
) -> list[Workflow]:
    now = datetime.now(UTC)
    specs = [
        {
            "name": "Invoice Processing Pipeline",
            "workflow_type": "invoice_processing",
            "status": WorkflowState.COMPLETED,
            "started_at": now - timedelta(hours=2),
            "completed_at": now - timedelta(hours=1),
            "output": {"invoices_processed": 3, "vouchers_created": 2},
        },
        {
            "name": "GST Reconciliation Run",
            "workflow_type": "gst_reconciliation",
            "status": WorkflowState.RUNNING,
            "started_at": now - timedelta(minutes=30),
            "completed_at": None,
            "output": {},
        },
        {
            "name": "Month-End Close",
            "workflow_type": "month_end_close",
            "status": WorkflowState.WAITING,
            "started_at": now - timedelta(hours=4),
            "completed_at": None,
            "output": {},
        },
    ]

    workflows: list[Workflow] = []
    for spec in specs:
        wf = Workflow(
            tenant_id=tenant_id,
            name=spec["name"],
            workflow_type=spec["workflow_type"],
            status=spec["status"],
            input_data={"seed": True, "period": "2026-03"},
            output_data=spec["output"],
            started_at=spec["started_at"],
            completed_at=spec["completed_at"],
            created_by=admin_user_id,
            assigned_agents=["ocr", "validation", "accounting"],
        )
        db.add(wf)
        await db.flush()

        for order, step_name in enumerate(["ocr_extract", "validate_gst", "create_voucher"], start=1):
            step_status = WorkflowState.COMPLETED if spec["status"] == WorkflowState.COMPLETED else (
                WorkflowState.RUNNING if order == 2 and spec["status"] == WorkflowState.RUNNING else WorkflowState.PENDING
            )
            db.add(WorkflowStep(
                tenant_id=tenant_id,
                workflow_id=wf.id,
                step_name=step_name,
                step_order=order,
                agent_name=step_name.split("_")[0],
                node_type="agent",
                step_type="task",
                status=step_status,
                started_at=spec["started_at"],
                completed_at=spec["completed_at"] if step_status == WorkflowState.COMPLETED else None,
            ))
        workflows.append(wf)

    await db.flush()
    return workflows


async def seed_approvals_and_audit(
    db: AsyncSession,
    tenant_id: UUID,
    admin_user_id: UUID,
    vouchers: list[VoucherDraft],
) -> None:
    pending_voucher = next((v for v in vouchers if v.approval_status == "pending"), vouchers[0])

    existing = await db.execute(
        select(ApprovalQueue).where(
            ApprovalQueue.tenant_id == tenant_id,
            ApprovalQueue.entity_id == pending_voucher.id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(ApprovalQueue(
            tenant_id=tenant_id,
            entity_type="voucher_draft",
            entity_id=pending_voucher.id,
            action="approve_voucher",
            status="pending",
            priority="high",
            title=f"Approve voucher {pending_voucher.voucher_number}",
            description="Purchase voucher pending manager approval",
            data={"amount": str(pending_voucher.total_amount), "party": pending_voucher.party_name},
            requested_by=admin_user_id,
        ))

    audit_events = [
        ("user.login", "User signed in successfully"),
        ("document.upload", "Uploaded purchase invoice PI-2026-0142"),
        ("ocr.process", "OCR pipeline completed for invoice"),
        ("voucher.create", f"Created voucher {pending_voucher.voucher_number}"),
        ("workflow.start", "Started GST Reconciliation workflow"),
    ]
    for action, description in audit_events:
        exists = await db.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == action,
                AuditLog.description == description,
            )
        )
        if exists.scalar_one_or_none():
            continue
        db.add(AuditLog(
            tenant_id=tenant_id,
            user_id=admin_user_id,
            action=action,
            entity_type="seed",
            description=description,
            metadata_={"seed": True},
        ))

    await db.flush()


async def seed_tenant_business_data(
    db: AsyncSession,
    tenant_id: UUID,
    tenant_slug: str,
    credentials: list[dict],
) -> bool:
    """Seed masters, transactions, extra users. Returns True if data was created."""
    if tenant_slug not in BUSINESS_DATA_TENANTS:
        await seed_extra_users(db, tenant_id, tenant_slug, credentials)
        return False

    if await _has_business_data(db, tenant_id):
        await seed_extra_users(db, tenant_id, tenant_slug, credentials)
        return False

    admin = await _get_admin_user(db, tenant_id)
    if not admin:
        return False

    await seed_extra_users(db, tenant_id, tenant_slug, credentials)
    masters = await seed_business_masters(db, tenant_id, admin.id)
    docs = await seed_documents(db, tenant_id, admin.id)
    vouchers = await seed_vouchers(db, tenant_id, admin.id, masters)
    await seed_workflows(db, tenant_id, admin.id)
    await seed_approvals_and_audit(db, tenant_id, admin.id, vouchers)
    return True
