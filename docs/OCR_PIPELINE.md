# Mahakosh OCR & Document Intelligence Pipeline

## Architecture

```
Upload → Classification → Preprocessing → PaddleOCR + Surya OCR
    → OCR Validation Agent → Consensus Engine → Layout Analysis
    → Table Extraction → Field Extraction → Validation
    → Confidence Scoring → Knowledge Object → Database
```

## Modules

| Module | Path | Responsibility |
|--------|------|----------------|
| Document Classifier | `document_classifier.py` | Indian business document type detection |
| Image Preprocessor | `image_preprocessor.py` | Deskew, denoise, contrast, rotation, shadows |
| OCR Engine | `ocr_engine.py` | Pluggable PaddleOCR + Surya (extensible registry) |
| OCR Validation Agent | `ocr_validation_agent.py` | Dual-engine field comparison |
| Consensus Engine | `consensus_engine.py` | Merges OCR outputs with confidence selection |
| Layout Analyzer | `layout_analyzer.py` | Headers, tables, GST blocks, totals |
| Table Extractor | `table_extractor.py` | pdfplumber, Camelot, Tabula |
| Field Extractor | `field_extractor.py` | Invoice fields, GSTIN, amounts, HSN |
| Document Validator | `document_validator.py` | GSTIN format, tax consistency |
| Confidence Engine | `confidence_engine.py` | Document/OCR/field/table confidence |
| Knowledge Builder | `knowledge_builder.py` | Embedding-ready knowledge objects |
| Pipeline Orchestrator | `pipeline_orchestrator.py` | End-to-end execution with stage logging |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ocr/upload` | Upload document, create OCR job |
| POST | `/api/v1/ocr/process` | Start OCR pipeline (background by default) |
| GET | `/api/v1/ocr/status/{job_id}` | Job status |
| GET | `/api/v1/ocr/result/{job_id}` | Full results with fields, tables, stages |
| GET | `/api/v1/ocr/validation/{job_id}` | Validation report |
| GET | `/api/v1/ocr/jobs` | List all OCR jobs |

## Database Tables

- `ocr_jobs` — Master job record with dual-engine outputs
- `ocr_pages` — Per-page Paddle/Surya/consensus text
- `ocr_fields` — Extracted fields with engine comparison
- `ocr_tables` — Structured table data
- `ocr_validation_results` — Validation report
- `ocr_confidence_scores` — Confidence by type
- `ocr_pipeline_stages` — Stage timing and errors

## Adding New OCR Engines

```python
from backend.services.document_intelligence.ocr_engine import BaseOCREngine, ocr_engine_registry

class EasyOCREngine(BaseOCREngine):
    name = "easyocr"
    def extract(self, image_paths, language="en"):
        ...

ocr_engine_registry.register(EasyOCREngine())
```

## Supported Inputs

PDF, JPG, JPEG, PNG, TIFF, multi-page PDF, scanned documents, mobile camera images, WhatsApp compressed images, thermal bills, colored invoices.
