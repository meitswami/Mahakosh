# Mahakosh Business Intelligence & Analytics Engine

**ज्ञान से निर्णय तक** — Users want answers and decisions, not raw data.

## Philosophy

- Documents, accounting twin, knowledge base, workflows, and agent data → actionable intelligence
- Natural language queries: "Why did expenses increase?", "What is my GST liability?"
- AI insights: observations, recommendations, warnings, opportunities with confidence scores

## Architecture

```
Accounting Twin (vouchers, parties, outstanding, stock items)
Workflow DB (workflows, metrics, approvals)
Documents / OCR / Sync jobs
        ↓
IntelligenceDataContext (single load per request)
        ↓
Intelligence Modules (financial, GST, vendors, customers, inventory, workflows, executive)
        ↓
Business Health Score + Anomaly Detection + Insights Engine
        ↓
API / Dashboards / Report Engine (PDF, Excel, CSV, Word)
```

## Folder Structure

```
backend/intelligence/
├── analytics/          # data_source, aggregators, anomaly_detector, insights_engine, operational
├── financial/          # profit, revenue, expense, cash flow trends
├── gst/                # liability, collections, anomalies
├── vendors/            # concentration, dependency, duplicates
├── customers/          # revenue contribution, risk scoring
├── inventory/          # dead stock, turnover, valuation
├── workflows/          # performance, approval delays, agent efficiency
├── executive/          # C-level dashboard, business health score
├── forecasting/        # revenue, purchase, inventory, cash flow projections
├── dashboards/         # dashboard builders per domain
├── reporting/          # PDF, Excel, CSV, Word export engine
└── service.py          # IntelligenceService orchestrator
```

## Intelligence Modules

| Module | Key Outputs |
|--------|-------------|
| Financial | Revenue/expense/profit trends, cash position, outstanding analysis |
| GST | Liability, ITC, trends, mismatch detection |
| Vendors | Top vendors, concentration risk, inactive/duplicate vendors |
| Customers | Top customers, receivables, risk scoring |
| Inventory | Dead stock, slow movers, valuation, turnover |
| Workflows | Success rate, approval delays, failure analysis |
| Executive | Unified C-level view + business health score (0–100) |

## Business Health Score

Weighted composite of:
- Revenue growth (20%)
- Cash position (15%)
- Outstanding receivables (15%)
- Inventory quality (15%)
- Compliance status (20%)
- Workflow efficiency (15%)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/intelligence/executive` | C-level dashboard |
| GET | `/api/v1/intelligence/financial` | Financial intelligence |
| GET | `/api/v1/intelligence/gst` | GST intelligence |
| GET | `/api/v1/intelligence/vendors` | Vendor intelligence |
| GET | `/api/v1/intelligence/customers` | Customer intelligence |
| GET | `/api/v1/intelligence/inventory` | Inventory intelligence |
| GET | `/api/v1/intelligence/workflows` | Workflow intelligence |
| GET | `/api/v1/intelligence/insights` | AI insights bundle |
| POST | `/api/v1/intelligence/query` | Natural language analytics |
| GET | `/api/v1/intelligence/forecasts` | Forecasting projections |
| GET | `/api/v1/intelligence/anomalies` | Anomaly detection |
| GET | `/api/v1/intelligence/dashboard/{type}` | Domain dashboard |
| POST | `/api/v1/intelligence/reports/generate` | Download report |
| POST | `/api/v1/reports/schedule` | Schedule recurring report |

## Database Tables (Migration 011)

- `analytics_reports` — generated report history
- `analytics_snapshots` — daily executive snapshots
- `forecast_results` — forecast persistence
- `anomaly_events` — detected anomalies
- `business_scores` — daily health scores
- `scheduled_reports` — daily/weekly/monthly/quarterly/yearly schedules

## Data Sources

Primary: `accounting_twin_objects` (normalized vouchers, parties, outstanding, stock items)

Fallback: `voucher_drafts` when twin is empty

Workflow: `workflows`, `workflow_metrics`, `approval_queue`

Operational: `documents`, `ocr_jobs`, `sync_jobs`

## Report Formats

- **Excel** — openpyxl with insights section
- **CSV** — tabular export
- **Word** — python-docx with tables and insights
- **PDF** — PyMuPDF generated summary

## Frontend

- **Intelligence Center** at `/intelligence` — executive overview, NL query, insights, report downloads
- **Dashboard** at `/dashboard` — live executive metrics (replaces mock data)
- **Reports** at `/reports` — template-based report generation

## Setup

1. Apply migration: `alembic upgrade head` (011)
2. Sync accounting data via Accounting Center (Tally import → digital twin)
3. Open Intelligence Center for live analytics

## Natural Language Examples

```
Why did expenses increase?
Which vendors grew fastest?
What is my GST liability?
Which customers are risky?
```

Responses include confidence scores and are computed from real twin/workflow data.
