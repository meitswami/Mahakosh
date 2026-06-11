"""Partner mode — CA firms, ERP vendors, SIs managing multiple client tenants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.platform import PartnerAccount, PartnerClient
from backend.models.tenant import Tenant
from backend.platform.tenant_provisioner import TenantProvisioner


class PartnerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provisioner = TenantProvisioner(db)

    async def register_partner(
        self,
        tenant_id: UUID,
        partner_type: str,
        company_name: str,
        contact_email: str,
        max_clients: int = 50,
    ) -> PartnerAccount:
        existing = await self.db.execute(
            select(PartnerAccount).where(PartnerAccount.tenant_id == tenant_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Partner account already exists for this tenant")

        partner = PartnerAccount(
            tenant_id=tenant_id,
            partner_type=partner_type,
            company_name=company_name,
            contact_email=contact_email,
            max_clients=max_clients,
            status="active",
        )
        self.db.add(partner)
        tenant = await self.db.get(Tenant, tenant_id)
        if tenant:
            tenant.tenant_type = "partner"
        await self.db.flush()
        return partner

    async def provision_client(
        self,
        partner_id: UUID,
        *,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str,
        admin_full_name: str,
        plan_tier: str = "professional",
    ) -> dict:
        partner = await self.db.get(PartnerAccount, partner_id)
        if not partner or partner.status != "active":
            raise ValueError("Partner account not found or inactive")

        client_count = (await self.db.execute(
            select(func.count()).select_from(PartnerClient).where(
                PartnerClient.partner_id == partner_id,
                PartnerClient.status == "active",
            )
        )).scalar() or 0

        if client_count >= partner.max_clients:
            raise ValueError(f"Partner client limit reached ({partner.max_clients})")

        result = await self.provisioner.provision(
            name=name,
            slug=slug,
            admin_email=admin_email,
            admin_password=admin_password,
            admin_full_name=admin_full_name,
            tenant_type="sme",
            plan_tier=plan_tier,
        )

        self.db.add(PartnerClient(
            partner_id=partner_id,
            client_tenant_id=UUID(result["tenant_id"]),
            client_name=name,
            status="active",
        ))
        await self.db.flush()
        return result

    async def list_clients(self, partner_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(PartnerClient, Tenant)
            .join(Tenant, Tenant.id == PartnerClient.client_tenant_id)
            .where(PartnerClient.partner_id == partner_id)
        )
        return [
            {
                "client_id": str(pc.id),
                "tenant_id": str(t.id),
                "name": t.display_name,
                "slug": t.slug,
                "status": pc.status,
                "is_active": t.is_active,
                "plan_tier": t.subscription_tier,
                "created_at": pc.created_at.isoformat(),
            }
            for pc, t in result.fetchall()
        ]

    async def get_partner_dashboard(self, partner_id: UUID) -> dict:
        clients = await self.list_clients(partner_id)
        partner = await self.db.get(PartnerAccount, partner_id)
        return {
            "partner": {
                "id": str(partner.id),
                "company_name": partner.company_name,
                "partner_type": partner.partner_type,
                "max_clients": partner.max_clients,
                "active_clients": len([c for c in clients if c["status"] == "active"]),
            },
            "clients": clients,
        }
