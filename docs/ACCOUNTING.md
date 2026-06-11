# Accounting Center — Tally Intelligence & Universal Connector Layer

Mahakosh is the **intelligence layer above Tally**, not a replacement. Phase 7 provides a universal accounting connector framework supporting Tally Prime, ERP 9, Silver, Gold, and future ERPs (Busy, Marg, ERPNext, Zoho Books).

## Architecture

```
Invoice → OCR → Knowledge → Agent Swarm → Accounting Intelligence → Voucher Draft → Approval → Tally Export
```

### Connector Priority

| Priority | Connector | Method |
|----------|-----------|--------|
| 1 | `TallyXMLConnector` | HTTP XML gateway (port 9000) |
| 2 | `TallyODBCConnector` | ODBC (Windows + Tally ODBC driver) |
| 3 | `FileSyncConnector` | Import/export/XML folder sync |
| 4 | `FutureERPConnector` | Extensible framework for other ERPs |

### Folder Structure

```
backend/connectors/accounting/
  base/          BaseAccountingConnector, registry, types
  tally/         TallyXMLConnector
  xml/           XML generator, parser, engine
  odbc/          ODBC driver, TallyODBCConnector
  sync/          SyncEngine, FileWatcher, FileSyncConnector
  mapping/       Smart matching engine
  validation/    Pre-export validation
  exports/       Export engine
  imports/       Import engine
  intelligence/  Ledger, Item, GST intelligence
  draft/         Voucher draft engine
```

## Database Tables (Migration 008)

- `accounting_connectors` — tenant connector configurations
- `tally_companies` — discovered Tally companies
- `ledger_mappings` / `item_mappings` — smart mapping with confidence
- `voucher_exports` — export audit trail
- `accounting_validations` — pre-export validation records
- `sync_jobs` / `sync_logs` — sync orchestration

## Digital Twin (Migration 009)

Mahakosh maintains a normalized **Accounting Digital Twin** independent of Tally structures. See [ACCOUNTING_TWIN.md](./ACCOUNTING_TWIN.md) for full architecture.

- `accounting_twin_objects` — normalized ledgers, items, parties, vouchers
- `accounting_normalization_jobs` — normalization job tracking
- `accounting_data_issues` — data quality issues
- `accounting_aliases` — name alias resolution

Import pipeline: **raw → normalizer → twin → knowledge → agents**

```
backend/connectors/accounting/
  twin/          Digital twin objects, normalizer, reality framework
  twin_knowledge_bridge.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounting/overview` | Accounting Center overview |
| POST | `/accounting/connect` | Create connector connection |
| POST | `/accounting/sync` | Run sync job |
| POST | `/accounting/import` | Import masters/transactions |
| POST | `/accounting/export` | Export reports |
| GET | `/accounting/companies` | List Tally companies |
| GET | `/accounting/ledgers` | Ledger browser |
| GET | `/accounting/items` | Item browser |
| GET | `/accounting/vouchers` | Voucher center |
| POST | `/accounting/vouchers/draft` | Create voucher draft |
| POST | `/accounting/vouchers/{id}/validate` | Validate before export |
| POST | `/accounting/vouchers/{id}/approve` | Approval gate |
| POST | `/accounting/vouchers/{id}/export` | Export to Tally |
| GET | `/accounting/mappings/ledgers` | Ledger mapping center |
| GET | `/accounting/sync/dashboard` | Sync dashboard |
| GET | `/accounting/twin/overview` | Digital twin stats & quality |
| GET | `/accounting/twin/ledgers` | Normalized ledger browser |
| GET | `/accounting/twin/items` | Normalized item browser |
| GET | `/accounting/twin/parties` | Normalized party browser |
| GET | `/accounting/twin/vouchers` | Normalized voucher browser |
| GET | `/accounting/twin/issues` | Data quality issues |
| POST | `/accounting/twin/normalize` | Trigger normalization job |
| POST | `/accounting/twin/resolve-issue` | Resolve data issue |
| POST | `/accounting/twin/merge-duplicate` | Merge duplicate objects |

## Approval Gate

Nothing exports directly. Flow: **Draft → Validation → Approval → Export**

## Agents

- `accounting` — voucher drafting with GST validation (v3.0)
- `tally` — Tally XML generation via connector layer (v2.0)
- Intelligence modules: `LedgerIntelligence`, `ItemIntelligence`, `GSTIntelligence`

## Workflows

`tally_export` workflow: `accounting → tally → audit`

## Setup

1. Run migration: `alembic upgrade head`
2. Enable Tally XML server (port 9000) or configure file-sync folders
3. Open **Accounting Center** at `/accounting`
4. Connect via Tally XML, ODBC, or File Sync
5. Sync ledgers/items, review mappings, approve vouchers, export

## File Sync Folders

Default paths (configurable per connector):

- `./tally/import` — inbound XML
- `./tally/export` — outbound voucher XML
- `./tally/xml` — company/master XML
