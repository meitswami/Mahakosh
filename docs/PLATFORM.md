# Mahakosh Platform — SaaS & Enterprise Architecture

**Phase 10** transforms Mahakosh from a single-application deployment into a production-grade multi-tenant SaaS platform supporting individual, SME, CA firm, enterprise, government, and partner deployments.

## Core Philosophy

```
One Codebase → Multiple Organizations → Complete Isolation → Independent Branding
```

## Tenant Types

| Type | Description |
|------|-------------|
| `individual` | Solo operators |
| `sme` | Small/medium businesses |
| `ca_firm` | Chartered accountant practices |
| `enterprise` | Large organizations with governance |
| `government` | Government deployments |
| `partner` | Resellers and system integrators |

## Database Tables

| Table | Purpose |
|-------|---------|
| `tenants` | Tenant registry (extended with `tenant_type`, `custom_domain`) |
| `tenant_settings` | Key-value tenant configuration |
| `tenant_branding` | White-label logo, theme, domain, email templates |
| `subscriptions` | Plan tier, billing cycle, trial/active status |
| `licenses` | License keys, expiry, renewal tracking |
| `usage_metrics` | Daily usage aggregates per metric type |
| `feature_flags` | Per-tenant feature overrides |
| `partner_accounts` | Partner registry linked to partner tenant |
| `partner_clients` | Partner → client tenant mapping |
| `billing_events` | Payment and billing audit trail |
| `governance_policies` | Retention, approval, audit policies |
| `security_events` | Security event log |

Migration: `013_platform_saas_tables.py`

## Tenant Provisioning Flow

```
New Customer
  → TenantProvisioner.provision()
  → Create Tenant + Roles + Admin User
  → Create Subscription + License
  → Default Settings + Branding
  → Storage prefix + Qdrant collections
  → Governance policies seeded
```

Public signup uses `POST /api/v1/auth/register` which delegates to `TenantProvisioner`.

Super-admin provisioning uses `POST /api/v1/tenants/create`.

## Subscription Plans

| Plan | OCR | Agents | Tally | Workflows | WhatsApp | Forecasting |
|------|-----|--------|-------|-----------|----------|-------------|
| Starter | ✓ | — | — | — | — | — |
| Professional | ✓ | ✓ | ✓ | ✓ | — | — |
| Enterprise | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| White Label | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Plan definitions: `backend/platform/plans.py`

## Feature Gating

`FeatureGate` resolves effective features from plan + per-tenant overrides in `feature_flags`.

Routes protected via `require_feature()` dependency:
- `/ocr` → `ocr`
- `/agents` → `agents`
- `/workflows` → `workflows`
- `/accounting` → `tally`
- `/intelligence/forecasts` → `forecasting`

## Usage Tracking

`UsageTracker` records daily aggregates:

- `documents_processed`
- `ocr_usage`
- `storage_bytes`
- `agent_executions`
- `workflow_runs`
- `api_calls`

Hooks are wired in OCR upload, agent execution, and workflow completion.

## API Endpoints

| Method | Path | Access |
|--------|------|--------|
| POST | `/api/v1/tenants/create` | Platform admin |
| GET | `/api/v1/tenants` | Platform admin |
| GET | `/api/v1/tenants/{id}` | Admin (own tenant) or platform admin |
| PUT | `/api/v1/tenants/{id}/branding` | Tenant admin |
| GET | `/api/v1/tenants/{id}/compliance` | Tenant admin |
| GET | `/api/v1/subscriptions` | Authenticated |
| GET | `/api/v1/subscriptions/current` | Authenticated |
| POST | `/api/v1/licenses` | Platform admin |
| GET | `/api/v1/usage` | Authenticated |
| GET | `/api/v1/platform/dashboard` | Platform admin |
| GET | `/api/v1/platform/partners/dashboard` | Partner tenant |
| POST | `/api/v1/platform/partners/clients` | Partner tenant |

## Partner Mode

Partners are registered via `PartnerAccount` linked to the partner's own tenant. Client tenants are provisioned through `PartnerService.provision_client()` and tracked in `partner_clients`.

## White Label

`tenant_branding` supports:
- Custom logo, favicon, colors
- Custom domain
- Custom login page title/subtitle
- Email templates and report headers/footers

## Security

- **Tenant isolation**: All data scoped by `tenant_id` via JWT
- **No cross-tenant access**: API routes validate `current_user.tenant_id`
- **Platform admin**: `users.is_platform_admin` gates super-admin routes
- **Trial enforcement**: Login blocked when trial expires without active subscription
- **Full auditability**: Governance center + audit logs

## Frontend

| Route | Purpose |
|-------|---------|
| `/register` | Self-service tenant signup |
| `/platform` | Super admin multi-tenant dashboard |
| `/admin/compliance` | Compliance center |
| `/admin` | Administration hub |

## Platform Admin Setup

Set `is_platform_admin = true` on a user record to enable super-admin access:

```sql
UPDATE users SET is_platform_admin = true WHERE email = 'admin@mahakosh.in';
```

Or run the platform seed (creates `admin@mahakosh.in` with platform admin flag).

## Database Seed

After migrations, seed demo tenants, partner clients, usage metrics, and App Store catalog:

```bash
# Start Postgres (Docker)
docker compose up -d postgres

# Migrate
cd backend && alembic upgrade head && cd ..

# Seed
python -m backend.scripts.seed_db
```

Windows (PowerShell):

```powershell
.\scripts\seed.ps1
```

**Default password (all seed accounts):** `Mahakosh@2026`

| Tenant | Slug | Email | Type |
|--------|------|-------|------|
| Platform | `mahakosh` | admin@mahakosh.in | enterprise (super admin) |
| Individual | `demo-individual` | raj@demo.mahakosh.in | individual |
| SME | `demo-sme` | owner@acme.demo.mahakosh.in | sme |
| CA Firm | `demo-ca` | partner@sharma-ca.demo.mahakosh.in | ca_firm |
| Enterprise | `demo-enterprise` | cfo@horizon.demo.mahakosh.in | enterprise |
| Government | `demo-government` | admin@gov-mh.demo.mahakosh.in | government |
| Partner | `demo-partner` | admin@finadvisors.demo.mahakosh.in | partner |
| Partner clients | `client-alpha`, `client-beta` | — | sme (provisioned) |

## Scalability Architecture (1 → 10,000 Tenants)

Mahakosh scales without architectural redesign through:

- **Tenant-scoped data model** — every entity carries `tenant_id`; queries always filter by JWT tenant
- **Stateless API layer** — horizontal pod autoscaling; no in-memory tenant state
- **Per-tenant storage isolation** — MinIO key prefix `{tenant_id}/`
- **Per-tenant vector collections** — Qdrant `{prefix}_{tenant_id}`
- **Connection pooling** — SQLAlchemy pool (20 + 10 overflow); upgrade pool per instance at scale
- **Usage metering** — daily aggregates in `usage_metrics` (partition-ready by `metric_date`)
- **Feature gating** — plan limits enforced at API layer before expensive operations
- **Plugin registry** — marketplace extensions load via `extension_catalog` + `ExtensionRegistry` without core redeploys

At 10,000 tenants: add read replicas, Redis session cache, async job queue (Temporal), and optional tenant-tier connection routing — no schema redesign required.

## App Store Foundation

Plugin architecture for future marketplaces:

| Marketplace | Extension Type | Registry |
|-------------|----------------|----------|
| Agent Marketplace | `agent` | `ExtensionRegistry` + `agent_registry` |
| Workflow Marketplace | `workflow` | `ExtensionRegistry` + `workflow_registry` |
| Connector Marketplace | `connector` | `ExtensionRegistry` + `accounting_connector_registry` |
| Industry Modules | `industry_module` | `extension_catalog` manifest |
| Third Party Extensions | `third_party` | `tenant_extension_installs` |

Tables (migration `014`):

- `extension_catalog` — published extensions with manifest JSON
- `tenant_extension_installs` — per-tenant enablement and config

Base plugin contract: `backend/extensions/base.py` (`BaseExtension.on_install`, `on_uninstall`, `health_check`)

Seed includes 5 catalog entries (GST agent, month-end workflow, Tally connector, retail pack, dashboard builder).

## Module Structure

```
backend/platform/
  plans.py              # Plan tiers and feature matrices
  feature_gate.py       # Feature gating dependency
  usage_tracker.py      # Usage metering
  tenant_provisioner.py # Full tenant provisioning
  partner_service.py    # Partner client management
  governance.py         # Compliance center
  service.py            # PlatformService orchestration
```
