# Mahakosh CEO Mode & AI CFO Foundation

**ज्ञान से निर्णय तक** — Business owners open Mahakosh and instantly understand their business without opening a single accounting report.

## CEO Mode — Four Questions

| Question | What it shows |
|----------|---------------|
| **What happened?** | Completed workflows, revenue changes, OCR/sync activity, closed events |
| **What is happening?** | Live workflows, active agents, in-progress operations |
| **What needs attention?** | Pending approvals, anomalies, compliance alerts, GST liability, data issues |
| **What should be done next?** | AI CFO recommendations (approval-gated) and strategic actions |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cfo/briefing` | Full CEO briefing (main entry point) |
| GET | `/api/v1/cfo/capabilities` | List AI CFO capabilities |
| GET | `/api/v1/cfo/recommendations` | Pending CFO recommendations |
| POST | `/api/v1/cfo/recommendations/{id}/approve` | Approve recommendation (admin) |
| POST | `/api/v1/cfo/recommendations/{id}/reject` | Reject recommendation (admin) |

## AI CFO Foundation

All capabilities implement `BaseCFOCapability`:

```python
class BaseCFOCapability(ABC):
    async def analyze(tenant_id, ctx, financial, workflow, health) -> CapabilityResult
    def recommend(ctx, financial, analysis) -> list[CFORecommendation]
    def requires_human_approval() -> bool  # always True
```

### Capabilities

| Capability | Purpose |
|------------|---------|
| `financial_recommendations` | Profit margin, expense optimization, payables/receivables balance |
| `cash_flow_planning` | Cash projections, runway, shortfall risk |
| `budget_monitoring` | Expense variance, expense-to-revenue ratio |
| `compliance_alerts` | GST anomalies, data quality, liability alerts |
| `strategic_insights` | Vendor concentration, customer risk, growth signals |

### Human Approval Gate

**No CFO recommendation executes automatically.**

Flow:
1. Capability analyzes data → generates `CFORecommendation`
2. `CFOApprovalGate.submit()` → stores as `pending_approval`
3. Admin approves or rejects via API
4. Only approved recommendations can proceed to execution (future phase)

## Architecture

```
Intelligence Layer (twin, workflows, anomalies, insights)
        ↓
AI CFO Capabilities (5 modules)
        ↓
CFOApprovalGate (human-in-the-loop)
        ↓
CEOBriefingSynthesizer (4-question briefing)
        ↓
CEO Mode Dashboard (/dashboard)
```

## Database (Migration 012)

- `cfo_briefings` — stored CEO briefings with full JSON payload
- `cfo_recommendations` — approval-tracked CFO recommendations

## Frontend

**CEO Mode** is the default landing experience at `/dashboard` (sidebar: "CEO Mode").

Sections map directly to the four CEO questions with priority badges, action links, and inline approve buttons for CFO recommendations.

## Future AI CFO Roadmap

Capabilities are architected for extension:
- Budget targets (planned vs actual from twin data)
- Automated cash flow scenarios
- Compliance calendar integration
- Strategic planning dashboards
- Execution engine (post-approval only)

All future capabilities must implement `BaseCFOCapability` and pass through `CFOApprovalGate`.
