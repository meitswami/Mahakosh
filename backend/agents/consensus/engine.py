from dataclasses import dataclass, field
from typing import Any

from backend.agents.base.types import ConfidenceLevel, confidence_level


@dataclass
class ConsensusVote:
    agent_name: str
    field: str
    value: Any
    confidence: float
    reasoning: str = ""


@dataclass
class ConsensusResult:
    field: str
    consensus_value: Any
    consensus_confidence: float
    confidence_level: ConfidenceLevel
    votes: list[ConsensusVote] = field(default_factory=list)
    agreement_ratio: float = 0.0
    accepted: bool = True
    dissenting_agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "consensus_value": self.consensus_value,
            "consensus_confidence": self.consensus_confidence,
            "confidence_level": self.confidence_level.value,
            "agreement_ratio": self.agreement_ratio,
            "accepted": self.accepted,
            "dissenting_agents": self.dissenting_agents,
            "votes": [
                {
                    "agent": v.agent_name,
                    "value": v.value,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                }
                for v in self.votes
            ],
        }


class ConsensusEngine:
    """Cross-agent validation via weighted voting on field values."""

    def compute(self, field: str, votes: list[ConsensusVote], min_agreement: float = 0.67) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                field=field,
                consensus_value=None,
                consensus_confidence=0.0,
                confidence_level=ConfidenceLevel.NEEDS_REVIEW,
                accepted=False,
            )

        value_weights: dict[str, float] = {}
        value_votes: dict[str, list[ConsensusVote]] = {}
        for vote in votes:
            key = str(vote.value)
            value_weights[key] = value_weights.get(key, 0.0) + vote.confidence
            value_votes.setdefault(key, []).append(vote)

        best_key = max(value_weights, key=value_weights.get)
        best_votes = value_votes[best_key]
        total_weight = sum(value_weights.values())
        agreement_ratio = value_weights[best_key] / total_weight if total_weight else 0.0
        avg_confidence = sum(v.confidence for v in best_votes) / len(best_votes)

        dissenting = [v.agent_name for v in votes if str(v.value) != best_key]
        accepted = agreement_ratio >= min_agreement and avg_confidence >= 80

        return ConsensusResult(
            field=field,
            consensus_value=best_votes[0].value,
            consensus_confidence=round(avg_confidence * agreement_ratio, 2),
            confidence_level=confidence_level(avg_confidence * agreement_ratio),
            votes=votes,
            agreement_ratio=round(agreement_ratio, 3),
            accepted=accepted,
            dissenting_agents=dissenting,
        )

    def compute_batch(self, vote_groups: dict[str, list[ConsensusVote]]) -> list[ConsensusResult]:
        return [self.compute(field, votes) for field, votes in vote_groups.items()]


consensus_engine = ConsensusEngine()
