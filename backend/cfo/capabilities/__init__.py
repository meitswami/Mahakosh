from backend.cfo.capabilities.budget_monitoring import BudgetMonitoringCapability
from backend.cfo.capabilities.cash_flow_planning import CashFlowPlanningCapability
from backend.cfo.capabilities.compliance_alerts import ComplianceAlertsCapability
from backend.cfo.capabilities.financial_recommendations import FinancialRecommendationsCapability
from backend.cfo.capabilities.strategic_insights import StrategicInsightsCapability

ALL_CAPABILITIES = [
    FinancialRecommendationsCapability,
    CashFlowPlanningCapability,
    BudgetMonitoringCapability,
    ComplianceAlertsCapability,
    StrategicInsightsCapability,
]

__all__ = [
    "ALL_CAPABILITIES",
    "FinancialRecommendationsCapability",
    "CashFlowPlanningCapability",
    "BudgetMonitoringCapability",
    "ComplianceAlertsCapability",
    "StrategicInsightsCapability",
]
