# Accounting Digital Twin — Indian Accounting Reality Framework

Mahakosh never depends directly on Tally structures. All external ERP data passes through a **Digital Twin** — a normalized, quality-scored representation of Indian accounting reality.

## Philosophy

Mahakosh **assists** users in cleaning and normalizing messy Indian accounting data. We never assume perfect records.

Real-world assumptions:
- Different Tally versions (Prime, ERP 9, Silver, Gold)
- Inconsistent ledger naming (`M/s ABC`, `Ms ABC`, `M/s. ABC Pvt Ltd`)
- Duplicate stock items with slight spelling differences
- Missing GST mappings and HSN codes
- Partial financial year data
- Non-standard voucher types (`Purc`, `Rcpt`, `Jrnl`)
- Non-standard accounting practices

## Architecture

```
External ERP (Tally / Busy / etc)
  → Import Adapters (connectors — Phase 7)
  → Normalization Engine (Indian Reality Framework)
  → Internal Accounting Objects (Digital Twin)
  → Knowledge Objects (knowledge base)
  → Agent Intelligence (via KnowledgeTool only)
```

Agents **never** receive raw Tally XML. They query the knowledge base built from twin objects.

## Folder Structure

```
backend/connectors/accounting/twin/
  objects.py      Normalized domain objects (ledger, item, party, voucher, etc.)
  reality.py      Indian Accounting Reality rules
  normalizer.py   Clean, score, detect duplicates, infer GST
  repository.py   Persistence layer
  service.py      Orchestration (import → normalize → persist → knowledge)

backend/connectors/accounting/twin_knowledge_bridge.py
  Twin objects → knowledge documents for search/chat
```

## Normalized Object Model

Each twin object carries:

| Field | Purpose |
|-------|---------|
| `source_system` | Connector type (`tally_xml`, `file_sync`, etc.) |
| `source_id` | Original ERP identifier |
| `raw_payload` | Untouched import data for audit |
| `normalized_fields` | Clean, ERP-independent fields |
| `quality_score` | 0–100 data quality score |
| `issues[]` | Detected problems with suggestions |
| `normalization_notes[]` | Auto-applied transformations |

Object types: `company`, `ledger`, `ledger_group`, `stock_item`, `unit`, `voucher`, `voucher_line`, `party`, `gst_profile`, `outstanding`.

## Indian Reality Rules

The `IndianAccountingReality` engine handles:

- **Ledger name variants** — strips `M/s`, `Shri`, normalizes `Pvt Ltd` / `LLP`
- **Duplicate detection** — fuzzy matching (≥82% similarity) + exact
- **GST inference** — HSN chapter → typical rate when rate missing
- **Non-standard voucher types** — maps `Purc` → `purchase`, etc.
- **Partial FY data** — flags short date spans in voucher imports
- **Quality scoring** — deducts for errors, warnings, missing fields

## Database Tables (Migration 009)

| Table | Purpose |
|-------|---------|
| `accounting_twin_objects` | Normalized objects per tenant |
| `accounting_normalization_jobs` | Re-normalization job tracking |
| `accounting_data_issues` | Open/resolved data quality issues |
| `accounting_aliases` | Name alias resolution (user merges + auto) |

## Import Pipeline

All imports follow:

```
connector.import_entities()
  → AccountingNormalizer.normalize_import()
  → TwinRepository.upsert_objects()
  → twin_knowledge_bridge.ingest_twin_knowledge()
  → legacy Ledger/Item tables (backward compatibility)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounting/twin/overview` | Twin stats, quality scores, suggestions |
| GET | `/accounting/twin/ledgers` | Normalized ledger browser |
| GET | `/accounting/twin/items` | Normalized stock items |
| GET | `/accounting/twin/parties` | Normalized vendors/customers |
| GET | `/accounting/twin/vouchers` | Normalized vouchers |
| GET | `/accounting/twin/issues` | Data quality issues |
| POST | `/accounting/twin/normalize` | Trigger re-normalization job |
| POST | `/accounting/twin/resolve-issue` | User resolves an issue |
| POST | `/accounting/twin/merge-duplicate` | Merge duplicate twin objects |

## Knowledge Bridge

Twin objects convert to searchable knowledge documents:

- Ledgers → `"Ledger: {name}"` with balance, GSTIN, quality
- Parties → vendor/customer profiles
- Items → HSN, GST rate, unit
- Vouchers → transaction patterns for GST liability queries
- Outstanding → receivable/payable summaries

Enables chat queries like *"top vendors"*, *"outstanding receivables"*, *"GST liability"* from twin data.

## Frontend

Accounting Center (`/accounting`) tabs:

- **Overview** — existing connector/sync/mapping UI
- **Data Quality** — issues, suggestions, quality scores, re-normalize
- **Digital Twin** — normalized ledgers, items, parties (not raw Tally)

## Migration

```bash
cd backend && alembic upgrade head
```

Applies `009_accounting_twin_tables.py`.

## Agent Integration

Intelligence modules (`LedgerIntelligence`, `ItemIntelligence`, `GSTIntelligence`) read from twin objects first, falling back to legacy tables. Agents still use `KnowledgeTool` / `WorkflowTool` / `ApprovalTool` only — never direct twin DB access.
