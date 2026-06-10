from typing import Any

from backend.agents.base.types import AgentResult
from backend.agents.consensus.engine import ConsensusEngine, ConsensusVote, consensus_engine


class SelfValidationFramework:
    """Agent A produces output → Agent B validates → Accept/Reject."""

    def __init__(self, engine: ConsensusEngine | None = None):
        self.engine = engine or consensus_engine

    def validate_field(
        self,
        producer: AgentResult,
        validator: AgentResult,
        field: str,
        producer_agent: str,
        validator_agent: str,
    ) -> dict[str, Any]:
        producer_val = producer.data.get(field)
        validator_val = validator.data.get(field)
        votes = [
            ConsensusVote(producer_agent, field, producer_val, producer.confidence, producer.reasoning),
            ConsensusVote(validator_agent, field, validator_val, validator.confidence, validator.reasoning),
        ]
        result = self.engine.compute(field, votes, min_agreement=0.5)
        return {
            "field": field,
            "accepted": result.accepted and producer_val == validator_val,
            "consensus": result.to_dict(),
            "producer_value": producer_val,
            "validator_value": validator_val,
        }


self_validator = SelfValidationFramework()
