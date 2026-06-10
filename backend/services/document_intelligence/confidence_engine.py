from backend.services.document_intelligence.types import (
    ClassificationResult,
    ConfidenceLevel,
    ConfidenceScores,
    ConsensusResult,
    ExtractedField,
    ExtractedTable,
    ValidationReport,
)


class ConfidenceEngine:
    """Calculates document, OCR, field, and table confidence scores."""

    HIGH_THRESHOLD = 0.80
    MEDIUM_THRESHOLD = 0.55

    def calculate(
        self,
        classification: ClassificationResult | None,
        consensus: ConsensusResult | None,
        fields: list[ExtractedField],
        tables: list[ExtractedTable],
        validation: ValidationReport | None,
    ) -> ConfidenceScores:
        ocr_score = consensus.consensus_confidence if consensus else 0.0
        field_score = self._field_confidence(fields)
        table_score = self._table_confidence(tables)
        doc_score = self._document_confidence(classification, ocr_score, field_score, table_score, validation)

        per_field = {f.field_name: f.confidence for f in fields if f.field_value}

        return ConfidenceScores(
            document=round(doc_score, 4),
            document_level=self._to_level(doc_score),
            ocr=round(ocr_score, 4),
            ocr_level=self._to_level(ocr_score),
            field=round(field_score, 4),
            field_level=self._to_level(field_score),
            table=round(table_score, 4),
            table_level=self._to_level(table_score),
            per_field=per_field,
        )

    def _field_confidence(self, fields: list[ExtractedField]) -> float:
        populated = [f for f in fields if f.field_value and not f.field_name.startswith("line_")]
        if not populated:
            return 0.0
        return sum(f.confidence for f in populated) / len(populated)

    def _table_confidence(self, tables: list[ExtractedTable]) -> float:
        if not tables:
            return 0.0
        return sum(t.confidence for t in tables) / len(tables)

    def _document_confidence(
        self,
        classification: ClassificationResult | None,
        ocr_score: float,
        field_score: float,
        table_score: float,
        validation: ValidationReport | None,
    ) -> float:
        weights = {"ocr": 0.30, "field": 0.35, "table": 0.15, "classification": 0.10, "validation": 0.10}
        score = ocr_score * weights["ocr"] + field_score * weights["field"] + table_score * weights["table"]

        if classification:
            score += classification.confidence * weights["classification"]

        if validation:
            error_count = len([i for i in validation.issues if i.severity == "error"])
            warning_count = len([i for i in validation.issues if i.severity == "warning"])
            validation_factor = max(0.0, 1.0 - (error_count * 0.15) - (warning_count * 0.05))
            score += validation_factor * weights["validation"]

        return min(score, 1.0)

    def _to_level(self, score: float) -> ConfidenceLevel:
        if score >= self.HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        if score >= self.MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @staticmethod
    def level_to_string(level: ConfidenceLevel) -> str:
        return level.value
