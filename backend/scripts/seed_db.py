#!/usr/bin/env python3
"""
Mahakosh platform database seed.

Provisions demo tenants, partner clients, usage metrics, App Store catalog,
business dummy data (vendors, customers, vouchers, workflows), and extra users.

Usage:
    python -m backend.scripts.seed_db
    python -m backend.scripts.seed_db --force   # re-seed missing records if mahakosh exists
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from backend.core.database import async_session_factory
from backend.models.extensions import ExtensionCatalog, TenantExtensionInstall
from backend.models.platform import UsageMetric
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.platform.governance import GovernanceService
from backend.platform.partner_service import PartnerService
from backend.platform.plans import PlanTier
from backend.platform.tenant_provisioner import TenantProvisioner
from backend.scripts.seed_business_data import (
    BUSINESS_DATA_TENANTS,
    DEFAULT_PASSWORD,
    seed_tenant_business_data,
)

SEED_TENANTS = [
    {
        "slug": "mahakosh",
        "name": "Mahakosh Platform",
        "tenant_type": "enterprise",
        "plan_tier": PlanTier.ENTERPRISE,
        "admin_email": "admin@mahakosh.in",
        "admin_name": "Platform Administrator",
        "is_platform_admin": True,
        "billing_cycle": "enterprise",
        "trial_days": 0,
    },
    {
        "slug": "demo-individual",
        "name": "Raj Kumar Trading",
        "tenant_type": "individual",
        "plan_tier": PlanTier.STARTER,
        "admin_email": "raj@demo.mahakosh.in",
        "admin_name": "Raj Kumar",
    },
    {
        "slug": "demo-sme",
        "name": "Acme Textiles Pvt Ltd",
        "tenant_type": "sme",
        "plan_tier": PlanTier.STARTER,
        "admin_email": "owner@acme.demo.mahakosh.in",
        "admin_name": "Priya Sharma",
    },
    {
        "slug": "demo-ca",
        "name": "Sharma & Associates CA",
        "tenant_type": "ca_firm",
        "plan_tier": PlanTier.PROFESSIONAL,
        "admin_email": "partner@sharma-ca.demo.mahakosh.in",
        "admin_name": "Amit Sharma",
    },
    {
        "slug": "demo-enterprise",
        "name": "Horizon Manufacturing Ltd",
        "tenant_type": "enterprise",
        "plan_tier": PlanTier.ENTERPRISE,
        "admin_email": "cfo@horizon.demo.mahakosh.in",
        "admin_name": "Neha Patel",
        "billing_cycle": "yearly",
        "trial_days": 0,
    },
    {
        "slug": "demo-government",
        "name": "Maharashtra Finance Department",
        "tenant_type": "government",
        "plan_tier": PlanTier.ENTERPRISE,
        "admin_email": "admin@gov-mh.demo.mahakosh.in",
        "admin_name": "Gov Admin",
        "billing_cycle": "enterprise",
        "trial_days": 0,
    },
    {
        "slug": "demo-partner",
        "name": "FinAdvisors Solutions",
        "tenant_type": "partner",
        "plan_tier": PlanTier.WHITE_LABEL,
        "admin_email": "admin@finadvisors.demo.mahakosh.in",
        "admin_name": "Vikram Mehta",
        "billing_cycle": "yearly",
        "trial_days": 0,
        "is_partner": True,
    },
]

EXTENSION_CATALOG = [
    {
        "extension_type": "agent",
        "slug": "gst-compliance-agent",
        "name": "GST Compliance Agent",
        "version": "1.0.0",
        "author": "Mahakosh",
        "description": "Automated GST return preparation and reconciliation agent.",
        "is_official": True,
        "manifest": {"entrypoint": "backend.extensions.stubs.gst_agent", "permissions": ["gst:read", "gst:write"]},
    },
    {
        "extension_type": "workflow",
        "slug": "month-end-close",
        "name": "Month-End Close Workflow",
        "version": "1.2.0",
        "author": "Mahakosh",
        "description": "End-to-end month-end accounting close with approval gates.",
        "is_official": True,
        "manifest": {"entrypoint": "backend.workflows.definitions.month_end", "steps": 8},
    },
    {
        "extension_type": "connector",
        "slug": "tally-premium-sync",
        "name": "Tally Premium Sync",
        "version": "2.1.0",
        "author": "Mahakosh",
        "description": "Bi-directional Tally ERP sync with conflict resolution.",
        "is_official": True,
        "manifest": {"connector_type": "tally", "sync_modes": ["import", "export", "bidirectional"]},
    },
    {
        "extension_type": "industry_module",
        "slug": "retail-inventory-pack",
        "name": "Retail Inventory Pack",
        "version": "1.0.0",
        "author": "Mahakosh",
        "description": "Industry templates for retail POS, inventory, and margin analytics.",
        "is_official": True,
        "manifest": {"industry": "retail", "templates": ["pos_daily", "stock_reorder", "margin_report"]},
    },
    {
        "extension_type": "third_party",
        "slug": "custom-dashboard-builder",
        "name": "Custom Dashboard Builder",
        "version": "0.9.0",
        "author": "Analytics Partners Inc",
        "description": "Drag-and-drop executive dashboard builder for white-label deployments.",
        "is_official": False,
        "manifest": {"entrypoint": "third_party.dashboard_builder", "requires": ["advanced_reporting"]},
    },
]

PARTNER_CLIENTS = [
    {
        "name": "Client Alpha Traders",
        "slug": "client-alpha",
        "admin_email": "admin@alpha.demo.mahakosh.in",
        "admin_full_name": "Alpha Admin",
        "plan_tier": PlanTier.PROFESSIONAL,
    },
    {
        "name": "Client Beta Industries",
        "slug": "client-beta",
        "admin_email": "admin@beta.demo.mahakosh.in",
        "admin_full_name": "Beta Admin",
        "plan_tier": PlanTier.PROFESSIONAL,
    },
]

ALL_TENANT_SLUGS = [t["slug"] for t in SEED_TENANTS] + [c["slug"] for c in PARTNER_CLIENTS]


def _build_admin_credentials() -> list[dict]:
    creds: list[dict] = []
    for spec in SEED_TENANTS:
        creds.append({
            "tenant_slug": spec["slug"],
            "email": spec["admin_email"],
            "password": DEFAULT_PASSWORD,
            "role": "admin",
            "full_name": spec["admin_name"],
            "tenant_type": spec["tenant_type"],
            "is_platform_admin": spec.get("is_platform_admin", False),
        })
    for client in PARTNER_CLIENTS:
        creds.append({
            "tenant_slug": client["slug"],
            "email": client["admin_email"],
            "password": DEFAULT_PASSWORD,
            "role": "admin",
            "full_name": client["admin_full_name"],
            "tenant_type": "sme",
            "is_platform_admin": False,
        })
    return creds


async def _tenant_exists(db, slug: str) -> bool:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none() is not None


async def _resolve_tenant_ids(db) -> dict[str, UUID]:
    result = await db.execute(select(Tenant).where(Tenant.slug.in_(ALL_TENANT_SLUGS)))
    return {t.slug: t.id for t in result.scalars().all()}


async def seed_extensions(db) -> dict[str, UUID]:
    catalog_ids: dict[str, UUID] = {}
    for item in EXTENSION_CATALOG:
        existing = await db.execute(
            select(ExtensionCatalog).where(
                ExtensionCatalog.extension_type == item["extension_type"],
                ExtensionCatalog.slug == item["slug"],
            )
        )
        record = existing.scalar_one_or_none()
        if record:
            catalog_ids[item["slug"]] = record.id
            continue
        record = ExtensionCatalog(**item)
        db.add(record)
        await db.flush()
        catalog_ids[item["slug"]] = record.id
    return catalog_ids


async def seed_usage(db, tenant_id: UUID) -> None:
    today = date.today()
    metrics = [
        ("documents_processed", [3, 5, 2, 8, 4, 6, 1, 9, 3, 7, 5, 4, 6, 2]),
        ("ocr_usage", [2, 3, 1, 4, 2, 3, 1, 5, 2, 4, 3, 2, 3, 1]),
        ("agent_executions", [1, 2, 0, 3, 1, 2, 0, 4, 1, 3, 2, 1, 2, 0]),
        ("workflow_runs", [0, 1, 1, 2, 0, 1, 1, 2, 1, 1, 0, 2, 1, 1]),
        ("api_calls", [120, 200, 150, 310, 180, 240, 90, 420, 190, 350, 210, 280, 160, 390]),
    ]
    for metric_type, daily_values in metrics:
        for offset, qty in enumerate(daily_values):
            metric_date = today - timedelta(days=len(daily_values) - offset)
            existing = await db.execute(
                select(UsageMetric).where(
                    UsageMetric.tenant_id == tenant_id,
                    UsageMetric.metric_type == metric_type,
                    UsageMetric.metric_date == metric_date,
                )
            )
            if existing.scalar_one_or_none():
                continue
            db.add(UsageMetric(
                tenant_id=tenant_id,
                metric_type=metric_type,
                metric_date=metric_date,
                quantity=qty,
            ))
    await db.flush()


def _write_credentials_file(credentials: list[dict], root: Path) -> Path:
    out = root / "seed_credentials.json"
    payload = {
        "password": DEFAULT_PASSWORD,
        "login_url": "http://localhost:3000/login",
        "recommended_demo": {
            "tenant_slug": "demo-sme",
            "email": "owner@acme.demo.mahakosh.in",
            "note": "Richest dummy data — vendors, vouchers, workflows, documents",
        },
        "accounts": credentials,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def _print_credentials(credentials: list[dict]) -> None:
    print("\n" + "=" * 72)
    print("LOGIN CREDENTIALS")
    print("=" * 72)
    print(f"Password (all accounts): {DEFAULT_PASSWORD}")
    print(f"Login URL:               http://localhost:3000/login\n")

    print(f"{'Tenant Slug':<20} {'Email':<38} {'Role':<12}")
    print("-" * 72)
    for c in sorted(credentials, key=lambda x: (x["tenant_slug"], x["role"] != "admin", x["email"])):
        slug = c["tenant_slug"]
        if c.get("is_platform_admin"):
            slug += " *"
        print(f"{slug:<20} {c['email']:<38} {c['role']:<12}")

    print("\n* = platform super admin (access /platform)")
    print("\nRecommended demo: demo-sme / owner@acme.demo.mahakosh.in")
    print("Full reference:   docs/SEED_CREDENTIALS.md")
    print("JSON export:      seed_credentials.json")
    print("=" * 72)


async def run_seed(force: bool = False) -> int:
    root = Path(__file__).resolve().parents[2]
    credentials: list[dict] = _build_admin_credentials()

    async with async_session_factory() as db:
        if await _tenant_exists(db, "mahakosh") and not force:
            print("Tenants exist — seeding missing dummy data and extensions only.")
            print("(Use --force on first run to create tenants from scratch.)\n")
        elif force and await _tenant_exists(db, "mahakosh"):
            print("WARNING: --force does not drop existing data; only missing records are created.\n")

        provisioner = TenantProvisioner(db)
        governance = GovernanceService(db)
        partner_svc = PartnerService(db)
        tenant_ids: dict[str, UUID] = await _resolve_tenant_ids(db)

        if not tenant_ids.get("mahakosh") or force:
            for spec in SEED_TENANTS:
                if await _tenant_exists(db, spec["slug"]):
                    continue

                result = await provisioner.provision(
                    name=spec["name"],
                    slug=spec["slug"],
                    admin_email=spec["admin_email"],
                    admin_password=DEFAULT_PASSWORD,
                    admin_full_name=spec["admin_name"],
                    tenant_type=spec["tenant_type"],
                    plan_tier=spec["plan_tier"],
                    billing_cycle=spec.get("billing_cycle", "monthly"),
                    trial_days=spec.get("trial_days", 14),
                    branding={
                        "login_title": spec["name"],
                        "login_subtitle": "ज्ञान से निर्णय तक",
                        "is_white_label": spec["plan_tier"] == PlanTier.WHITE_LABEL,
                    },
                )
                tenant_id = UUID(result["tenant_id"])
                tenant_ids[spec["slug"]] = tenant_id
                await governance.seed_default_policies(tenant_id)

                if spec.get("is_platform_admin"):
                    user = await db.get(User, UUID(result["admin_user_id"]))
                    if user:
                        user.is_platform_admin = True

                if spec.get("is_partner"):
                    partner = await partner_svc.register_partner(
                        tenant_id,
                        "system_integrator",
                        spec["name"],
                        spec["admin_email"],
                        max_clients=50,
                    )
                    for client in PARTNER_CLIENTS:
                        if not await _tenant_exists(db, client["slug"]):
                            await partner_svc.provision_client(
                                partner.id, **client, admin_password=DEFAULT_PASSWORD,
                            )

                print(f"  seed  tenant {spec['slug']}")

        tenant_ids = await _resolve_tenant_ids(db)

        catalog_ids = await seed_extensions(db)
        print(f"  seed  extension catalog ({len(catalog_ids)} items)")

        enterprise_id = tenant_ids.get("demo-enterprise")
        if enterprise_id and "tally-premium-sync" in catalog_ids:
            existing_install = await db.execute(
                select(TenantExtensionInstall).where(
                    TenantExtensionInstall.tenant_id == enterprise_id,
                    TenantExtensionInstall.extension_id == catalog_ids["tally-premium-sync"],
                )
            )
            if not existing_install.scalar_one_or_none():
                db.add(TenantExtensionInstall(
                    tenant_id=enterprise_id,
                    extension_id=catalog_ids["tally-premium-sync"],
                    enabled=True,
                    config={"sync_mode": "bidirectional"},
                ))

        business_seeded = 0
        for slug, tenant_id in tenant_ids.items():
            if await seed_tenant_business_data(db, tenant_id, slug, credentials):
                business_seeded += 1
                print(f"  seed  business data ({slug})")

        for slug in ("demo-sme", "demo-enterprise", "demo-ca"):
            tid = tenant_ids.get(slug)
            if tid:
                await seed_usage(db, tid)
        print("  seed  usage metrics (demo-sme, demo-enterprise, demo-ca)")

        await db.commit()

        cred_path = _write_credentials_file(credentials, root)

        print("\n" + "=" * 72)
        print("MAHAKOSH DATABASE SEEDED SUCCESSFULLY")
        print("=" * 72)
        print(f"Tenants:        {len(tenant_ids)}")
        print(f"Business data:  {business_seeded} tenant(s) with full dummy dataset")
        print(f"Dummy data on:  {', '.join(BUSINESS_DATA_TENANTS)}")
        _print_credentials(credentials)
        print(f"\nCredentials saved to: {cred_path}")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Mahakosh platform database")
    parser.add_argument("--force", action="store_true", help="Create tenants even if some already exist")
    args = parser.parse_args()
    try:
        code = asyncio.run(run_seed(force=args.force))
        sys.exit(code)
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
