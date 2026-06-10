from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledge import KnowledgeDocument, KnowledgeRelationship
from backend.services.knowledge.types import GraphNodeType, GraphRelationshipType, KnowledgeObject


class KnowledgeGraphBuilder:
    """Builds knowledge relationships — graph-ready for future Neo4j integration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_from_object(
        self,
        tenant_id: UUID,
        document: KnowledgeDocument,
        obj: KnowledgeObject,
    ) -> list[KnowledgeRelationship]:
        relationships: list[KnowledgeRelationship] = []

        doc_rel = KnowledgeRelationship(
            tenant_id=tenant_id,
            source_document_id=document.id,
            source_entity_type=GraphNodeType.DOCUMENT.value,
            source_entity_id=str(document.id),
            target_entity_type=GraphNodeType.DOCUMENT.value,
            target_entity_id=str(document.id),
            relationship_type=GraphRelationshipType.CONTAINS.value,
            confidence=1.0,
            metadata_={"title": document.title},
            graph_ready=True,
        )
        relationships.append(doc_rel)

        fields = obj.structured_fields or {}

        if fields.get("vendor_name"):
            relationships.append(self._rel(
                tenant_id, document.id,
                GraphNodeType.VENDOR, fields["vendor_name"],
                GraphRelationshipType.REFERENCES,
            ))

        if fields.get("customer_name"):
            relationships.append(self._rel(
                tenant_id, document.id,
                GraphNodeType.CUSTOMER, fields["customer_name"],
                GraphRelationshipType.REFERENCES,
            ))

        if fields.get("invoice_number"):
            relationships.append(self._rel(
                tenant_id, document.id,
                GraphNodeType.INVOICE, fields["invoice_number"],
                GraphRelationshipType.CONTAINS,
            ))

        for table in obj.tables or []:
            if table.get("table_type") == "line_items":
                for row in table.get("rows", [])[:20]:
                    if row:
                        item_name = row[0] if row else None
                        if item_name:
                            relationships.append(self._rel(
                                tenant_id, document.id,
                                GraphNodeType.ITEM, str(item_name),
                                GraphRelationshipType.CONTAINS,
                                confidence=0.8,
                            ))

        if obj.document_type in ("purchase_invoice", "invoice", "gst_invoice"):
            relationships.append(KnowledgeRelationship(
                tenant_id=tenant_id,
                source_document_id=document.id,
                source_entity_type=GraphNodeType.VENDOR.value,
                source_entity_id=fields.get("vendor_name"),
                target_entity_type=GraphNodeType.INVOICE.value,
                target_entity_id=fields.get("invoice_number"),
                relationship_type=GraphRelationshipType.PURCHASED.value,
                confidence=0.85,
                graph_ready=True,
            ))

        for rel in relationships:
            self.db.add(rel)

        await self.db.flush()
        return relationships

    def _rel(
        self,
        tenant_id: UUID,
        doc_id: UUID,
        target_type: GraphNodeType,
        target_id: str,
        rel_type: GraphRelationshipType,
        confidence: float = 0.9,
    ) -> KnowledgeRelationship:
        return KnowledgeRelationship(
            tenant_id=tenant_id,
            source_document_id=doc_id,
            source_entity_type=GraphNodeType.DOCUMENT.value,
            source_entity_id=str(doc_id),
            target_entity_type=target_type.value,
            target_entity_id=target_id,
            relationship_type=rel_type.value,
            confidence=confidence,
            graph_ready=True,
        )

    def to_neo4j_export(self, relationships: list[KnowledgeRelationship]) -> dict:
        nodes = {}
        edges = []
        for rel in relationships:
            src_key = f"{rel.source_entity_type}:{rel.source_entity_id}"
            tgt_key = f"{rel.target_entity_type}:{rel.target_entity_id}"
            nodes[src_key] = {"type": rel.source_entity_type, "id": rel.source_entity_id}
            nodes[tgt_key] = {"type": rel.target_entity_type, "id": rel.target_entity_id}
            edges.append({
                "source": src_key,
                "target": tgt_key,
                "type": rel.relationship_type,
                "confidence": rel.confidence,
            })
        return {"nodes": list(nodes.values()), "edges": edges}
