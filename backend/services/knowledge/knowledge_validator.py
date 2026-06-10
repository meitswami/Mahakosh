from backend.services.knowledge.types import KnowledgeObject


class KnowledgeValidator:
    """Validates knowledge objects for traceability, auditability, and explainability."""

    REQUIRED_FIELDS = ["title", "source"]
    RECOMMENDED_FIELDS = ["document_type", "raw_text"]

    def validate(self, obj: KnowledgeObject) -> dict:
        issues: list[dict] = []
        passed: list[str] = []
        failed: list[str] = []

        for field in self.REQUIRED_FIELDS:
            value = getattr(obj, field, None)
            if value:
                passed.append(f"required_{field}")
            else:
                issues.append({"code": f"MISSING_{field.upper()}", "severity": "error", "field": field})
                failed.append(f"required_{field}")

        for field in self.RECOMMENDED_FIELDS:
            value = getattr(obj, field, None)
            if value:
                passed.append(f"recommended_{field}")
            else:
                issues.append({"code": f"MISSING_{field.upper()}", "severity": "warning", "field": field})

        if not obj.raw_text or len(obj.raw_text.strip()) < 10:
            issues.append({"code": "INSUFFICIENT_CONTENT", "severity": "warning", "message": "Raw text too short"})
            failed.append("content_length")
        else:
            passed.append("content_length")

        if not obj.metadata.get("source") and not obj.source:
            issues.append({"code": "NO_TRACEABILITY", "severity": "error", "message": "Source traceability missing"})
            failed.append("traceability")
        else:
            passed.append("traceability")

        explainability_score = self._explainability_score(obj)
        if explainability_score < 0.3:
            issues.append({"code": "LOW_EXPLAINABILITY", "severity": "info", "score": explainability_score})
        else:
            passed.append("explainability")

        return {
            "is_valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "checks_passed": passed,
            "checks_failed": failed,
            "explainability_score": explainability_score,
            "audit_trail": {
                "source": obj.source,
                "document_type": obj.document_type,
                "has_structured_fields": bool(obj.structured_fields),
                "has_tables": bool(obj.tables),
                "has_relationships": bool(obj.relationships),
                "tag_count": len(obj.tags),
            },
        }

    def _explainability_score(self, obj: KnowledgeObject) -> float:
        score = 0.0
        if obj.source:
            score += 0.2
        if obj.structured_fields:
            score += 0.25
        if obj.tables:
            score += 0.15
        if obj.metadata:
            score += 0.15
        if obj.confidence is not None:
            score += 0.15
        if obj.tags:
            score += 0.1
        return min(score, 1.0)
