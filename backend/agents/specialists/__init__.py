"""Plugin-based specialist agent registration."""

from backend.agents.registry.registry import agent_registry
from backend.agents.specialists.accounting import AccountingAgent
from backend.agents.specialists.approval import ApprovalAgent
from backend.agents.specialists.audit import AuditAgent
from backend.agents.specialists.gst import GSTAgent
from backend.agents.specialists.hsn import HSNAgent
from backend.agents.specialists.item import ItemAgent
from backend.agents.specialists.ocr import OCRAgent
from backend.agents.specialists.reporting import ReportingAgent
from backend.agents.specialists.search import SearchAgent
from backend.agents.specialists.tally import TallyAgent
from backend.agents.specialists.validation import ValidationAgent
from backend.agents.specialists.vendor import VendorAgent
from backend.agents.specialists.workflow import WorkflowAgent
from backend.agents.orchestrator.master import MasterOrchestratorAgent

ALL_AGENTS = [
    MasterOrchestratorAgent,
    OCRAgent,
    ValidationAgent,
    VendorAgent,
    ItemAgent,
    GSTAgent,
    HSNAgent,
    AccountingAgent,
    SearchAgent,
    ReportingAgent,
    WorkflowAgent,
    AuditAgent,
    ApprovalAgent,
    TallyAgent,
]

for agent_cls in ALL_AGENTS:
    agent_registry.register(agent_cls)

__all__ = [cls.__name__ for cls in ALL_AGENTS] + ["ALL_AGENTS", "agent_registry"]
