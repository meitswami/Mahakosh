import difflib
import re
from typing import Any

from backend.services.document_intelligence.types import (
    BoundingBox,
    ConsensusResult,
    OCREngineOutput,
    OCRPageOutput,
    OCRToken,
)


class ConsensusEngine:
    """Multi-OCR consensus: merges PaddleOCR and Surya outputs into a single reliable result."""

    def build_consensus(
        self,
        paddle_output: OCREngineOutput | None,
        surya_output: OCREngineOutput | None,
        field_comparison: dict[str, Any] | None = None,
    ) -> ConsensusResult:
        if paddle_output is None and surya_output is None:
            raise ValueError("At least one OCR engine output is required")

        if paddle_output is None:
            return ConsensusResult(
                final_output=surya_output,  # type: ignore[arg-type]
                paddle_output=None,
                surya_output=surya_output,
                consensus_confidence=surya_output.pages[0].average_confidence if surya_output.pages else 0.0,
            )

        if surya_output is None:
            return ConsensusResult(
                final_output=paddle_output,
                paddle_output=paddle_output,
                surya_output=None,
                consensus_confidence=paddle_output.pages[0].average_confidence if paddle_output.pages else 0.0,
            )

        page_count = max(len(paddle_output.pages), len(surya_output.pages))
        merged_pages: list[OCRPageOutput] = []
        differences: list[dict[str, Any]] = []
        engine_selections: dict[str, str] = {}

        for page_num in range(1, page_count + 1):
            paddle_page = self._get_page(paddle_output, page_num)
            surya_page = self._get_page(surya_output, page_num)
            merged_page, page_diffs, selections = self._merge_pages(paddle_page, surya_page, page_num)
            merged_pages.append(merged_page)
            differences.extend(page_diffs)
            engine_selections.update(selections)

        if field_comparison:
            for field_name, comparison in field_comparison.items():
                selected = comparison.get("selected_engine", "consensus")
                engine_selections[field_name] = selected
                if comparison.get("paddle_value") != comparison.get("surya_value"):
                    differences.append({
                        "field": field_name,
                        "paddle": comparison.get("paddle_value"),
                        "surya": comparison.get("surya_value"),
                        "selected": comparison.get("consensus_value"),
                        "reason": comparison.get("reason", "field_comparison"),
                    })

        confidences = [p.average_confidence for p in merged_pages if p.tokens]
        consensus_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        final_output = OCREngineOutput(
            engine_name="consensus",
            pages=merged_pages,
            processing_time_ms=paddle_output.processing_time_ms + surya_output.processing_time_ms,
            raw_response={
                "paddle_time_ms": paddle_output.processing_time_ms,
                "surya_time_ms": surya_output.processing_time_ms,
            },
        )

        return ConsensusResult(
            final_output=final_output,
            paddle_output=paddle_output,
            surya_output=surya_output,
            field_differences=differences,
            selected_engine_per_field=engine_selections,
            consensus_confidence=round(consensus_confidence, 4),
        )

    def _get_page(self, output: OCREngineOutput, page_number: int) -> OCRPageOutput | None:
        for page in output.pages:
            if page.page_number == page_number:
                return page
        return None

    def _merge_pages(
        self,
        paddle_page: OCRPageOutput | None,
        surya_page: OCRPageOutput | None,
        page_number: int,
    ) -> tuple[OCRPageOutput, list[dict[str, Any]], dict[str, str]]:
        differences: list[dict[str, Any]] = []
        selections: dict[str, str] = {}

        if paddle_page is None and surya_page is None:
            return OCRPageOutput(page_number=page_number, width=0, height=0), differences, selections

        if paddle_page is None:
            return surya_page, differences, selections  # type: ignore[return-value]

        if surya_page is None:
            return paddle_page, differences, selections

        paddle_text = paddle_page.full_text.strip()
        surya_text = surya_page.full_text.strip()
        similarity = difflib.SequenceMatcher(None, paddle_text, surya_text).ratio()

        if similarity > 0.92:
            selected_page = paddle_page if paddle_page.average_confidence >= surya_page.average_confidence else surya_page
            selections[f"page_{page_number}_text"] = selected_page.metadata.get("engine", "consensus")
            return selected_page, differences, selections

        merged_tokens = self._merge_tokens(paddle_page.tokens, surya_page.tokens)
        merged_text = "\n".join(t.text for t in merged_tokens)
        differences.append({
            "page": page_number,
            "type": "text_divergence",
            "similarity": round(similarity, 4),
            "paddle_length": len(paddle_text),
            "surya_length": len(surya_text),
        })
        selections[f"page_{page_number}_text"] = "consensus_merge"

        return OCRPageOutput(
            page_number=page_number,
            width=max(paddle_page.width, surya_page.width),
            height=max(paddle_page.height, surya_page.height),
            tokens=merged_tokens,
            full_text=merged_text,
            metadata={"engine": "consensus", "paddle_conf": paddle_page.average_confidence, "surya_conf": surya_page.average_confidence},
        ), differences, selections

    def _merge_tokens(self, paddle_tokens: list[OCRToken], surya_tokens: list[OCRToken]) -> list[OCRToken]:
        merged: list[OCRToken] = []
        used_surya: set[int] = set()

        for p_token in paddle_tokens:
            best_match: OCRToken | None = None
            best_score = 0.0
            best_idx = -1

            for idx, s_token in enumerate(surya_tokens):
                if idx in used_surya:
                    continue
                text_sim = difflib.SequenceMatcher(None, p_token.text.lower(), s_token.text.lower()).ratio()
                iou = self._bbox_iou(p_token.bbox, s_token.bbox)
                score = 0.6 * text_sim + 0.4 * iou
                if score > best_score and score > 0.5:
                    best_score = score
                    best_match = s_token
                    best_idx = idx

            if best_match and best_score > 0.75:
                used_surya.add(best_idx)
                selected = p_token if p_token.confidence >= best_match.confidence else best_match
                merged.append(selected)
            else:
                merged.append(p_token)

        for idx, s_token in enumerate(surya_tokens):
            if idx not in used_surya:
                merged.append(s_token)

        merged.sort(key=lambda t: (t.bbox.y1, t.bbox.x1))
        return merged

    def _bbox_iou(self, a: BoundingBox, b: BoundingBox) -> float:
        x1 = max(a.x1, b.x1)
        y1 = max(a.y1, b.y1)
        x2 = min(a.x2, b.x2)
        y2 = min(a.y2, b.y2)
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        union = a.area + b.area - intersection
        return intersection / union if union > 0 else 0.0
