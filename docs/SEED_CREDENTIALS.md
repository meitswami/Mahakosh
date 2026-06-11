# Mahakosh Seed Login Credentials

All seed accounts use the same password unless noted otherwise.

**Password:** `Mahakosh@2026`

**Login URL:** `http://localhost:3000/login`

---

## Platform Super Admin

| Tenant Slug | Email | Role | Portal |
|-------------|-------|------|--------|
| `mahakosh` | admin@mahakosh.in | Platform Admin | `/platform` |

---

## Demo Tenants — Admin Accounts

| Tenant Slug | Email | Role | Tenant Type |
|-------------|-------|------|-------------|
| `demo-individual` | raj@demo.mahakosh.in | Admin | Individual |
| `demo-sme` | owner@acme.demo.mahakosh.in | Admin | SME |
| `demo-ca` | partner@sharma-ca.demo.mahakosh.in | Admin | CA Firm |
| `demo-enterprise` | cfo@horizon.demo.mahakosh.in | Admin | Enterprise |
| `demo-government` | admin@gov-mh.demo.mahakosh.in | Admin | Government |
| `demo-partner` | admin@finadvisors.demo.mahakosh.in | Admin | Partner |

---

## Demo Tenants — Additional Users

### demo-sme (Acme Textiles)

| Email | Role | Name |
|-------|------|------|
| manager@acme.demo.mahakosh.in | Manager | Ravi Mehta |
| accountant@acme.demo.mahakosh.in | Accountant | Sneha Desai |
| viewer@acme.demo.mahakosh.in | Viewer | Karan Joshi |

### demo-enterprise (Horizon Manufacturing)

| Email | Role | Name |
|-------|------|------|
| manager@horizon.demo.mahakosh.in | Manager | Arjun Singh |
| accountant@horizon.demo.mahakosh.in | Accountant | Divya Rao |
| auditor@horizon.demo.mahakosh.in | Auditor | Meera Iyer |

### demo-ca (Sharma & Associates)

| Email | Role | Name |
|-------|------|------|
| manager@sharma-ca.demo.mahakosh.in | Manager | Rohit Verma |
| staff@sharma-ca.demo.mahakosh.in | Accountant | Pooja Gupta |

### demo-partner (FinAdvisors)

| Email | Role | Name |
|-------|------|------|
| ops@finadvisors.demo.mahakosh.in | Manager | Anita Kulkarni |

---

## Partner Client Tenants

| Tenant Slug | Email | Role |
|-------------|-------|------|
| `client-alpha` | admin@alpha.demo.mahakosh.in | Admin |
| `client-alpha` | finance@alpha.demo.mahakosh.in | Accountant |
| `client-beta` | admin@beta.demo.mahakosh.in | Admin |

---

## Dummy Business Data (after seed)

Seeded for `demo-sme`, `demo-enterprise`, `demo-ca`, `client-alpha`:

- **4 vendors** — Reliance, Tata Steel, Infosys, Local Stationery Mart
- **3 customers** — Metro Retail, Green Farms, TechStart
- **4 items** — Cotton Fabric, Polyester Yarn, Industrial Dye, Packaging Carton
- **6 ledgers** — Purchase, Sales, CGST/SGST Payable, HDFC Bank, Cash
- **5 documents** — invoices, bank statement, GST return, credit note
- **3 voucher drafts** — purchase & sales with GST lines
- **3 workflows** — completed, running, waiting for approval
- **Approval queue** — pending voucher approval
- **Audit log** — sample security & business events

**Recommended demo login:** `demo-sme` / `owner@acme.demo.mahakosh.in` — richest dataset for UI walkthrough.

---

## Quick Start

```bash
docker compose up -d postgres
cd backend && alembic upgrade head && cd ..
python -m backend.scripts.seed_db
```

Or: `.\scripts\seed.ps1`
