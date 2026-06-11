"""Subscription plan definitions and feature matrices."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class PlanTier(StrEnum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    WHITE_LABEL = "white_label"
    LIFETIME = "lifetime"


class BillingCycle(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"
    ENTERPRISE = "enterprise"


PLAN_DEFINITIONS: dict[str, dict[str, Any]] = {
    PlanTier.STARTER: {
        "name": "Starter",
        "display_name": "Starter",
        "billing_cycles": [BillingCycle.MONTHLY, BillingCycle.YEARLY],
        "max_users": 3,
        "max_storage_gb": 5,
        "max_documents_per_month": 100,
        "max_ocr_per_month": 50,
        "max_workflow_runs_per_month": 20,
        "max_agent_executions_per_month": 50,
        "max_api_calls_per_month": 5000,
        "features": {
            "ocr": True,
            "agents": False,
            "tally": False,
            "workflows": True,
            "whatsapp": False,
            "telegram": False,
            "forecasting": False,
            "advanced_reporting": False,
            "white_label": False,
            "partner_mode": False,
            "sso": False,
            "api_access": False,
        },
        "price_monthly_inr": 2999,
        "price_yearly_inr": 29990,
    },
    PlanTier.PROFESSIONAL: {
        "name": "Professional",
        "display_name": "Professional",
        "billing_cycles": [BillingCycle.MONTHLY, BillingCycle.YEARLY],
        "max_users": 15,
        "max_storage_gb": 50,
        "max_documents_per_month": 1000,
        "max_ocr_per_month": 500,
        "max_workflow_runs_per_month": 200,
        "max_agent_executions_per_month": 500,
        "max_api_calls_per_month": 50000,
        "features": {
            "ocr": True,
            "agents": True,
            "tally": True,
            "workflows": True,
            "whatsapp": True,
            "telegram": True,
            "forecasting": True,
            "advanced_reporting": True,
            "white_label": False,
            "partner_mode": False,
            "sso": False,
            "api_access": True,
        },
        "price_monthly_inr": 9999,
        "price_yearly_inr": 99990,
    },
    PlanTier.ENTERPRISE: {
        "name": "Enterprise",
        "display_name": "Enterprise",
        "billing_cycles": [BillingCycle.MONTHLY, BillingCycle.YEARLY, BillingCycle.ENTERPRISE],
        "max_users": 500,
        "max_storage_gb": 500,
        "max_documents_per_month": 50000,
        "max_ocr_per_month": 10000,
        "max_workflow_runs_per_month": 5000,
        "max_agent_executions_per_month": 10000,
        "max_api_calls_per_month": 500000,
        "features": {
            "ocr": True,
            "agents": True,
            "tally": True,
            "workflows": True,
            "whatsapp": True,
            "telegram": True,
            "forecasting": True,
            "advanced_reporting": True,
            "white_label": False,
            "partner_mode": True,
            "sso": True,
            "api_access": True,
        },
        "price_monthly_inr": 49999,
        "price_yearly_inr": 499990,
    },
    PlanTier.WHITE_LABEL: {
        "name": "White Label",
        "display_name": "White Label",
        "billing_cycles": [BillingCycle.YEARLY, BillingCycle.LIFETIME, BillingCycle.ENTERPRISE],
        "max_users": 1000,
        "max_storage_gb": 1000,
        "max_documents_per_month": 100000,
        "max_ocr_per_month": 50000,
        "max_workflow_runs_per_month": 20000,
        "max_agent_executions_per_month": 50000,
        "max_api_calls_per_month": 1000000,
        "features": {
            "ocr": True,
            "agents": True,
            "tally": True,
            "workflows": True,
            "whatsapp": True,
            "telegram": True,
            "forecasting": True,
            "advanced_reporting": True,
            "white_label": True,
            "partner_mode": True,
            "sso": True,
            "api_access": True,
        },
        "price_yearly_inr": 999990,
        "price_lifetime_inr": 2999990,
    },
    PlanTier.LIFETIME: {
        "name": "Lifetime",
        "display_name": "Lifetime",
        "billing_cycles": [BillingCycle.LIFETIME],
        "max_users": 25,
        "max_storage_gb": 100,
        "max_documents_per_month": 2000,
        "max_ocr_per_month": 1000,
        "max_workflow_runs_per_month": 500,
        "max_agent_executions_per_month": 1000,
        "max_api_calls_per_month": 100000,
        "features": {
            "ocr": True,
            "agents": True,
            "tally": True,
            "workflows": True,
            "whatsapp": True,
            "telegram": True,
            "forecasting": True,
            "advanced_reporting": True,
            "white_label": False,
            "partner_mode": False,
            "sso": False,
            "api_access": True,
        },
        "price_lifetime_inr": 149990,
    },
}


def get_plan(plan_tier: str) -> dict[str, Any]:
    return PLAN_DEFINITIONS.get(plan_tier, PLAN_DEFINITIONS[PlanTier.STARTER])


def plan_has_feature(plan_tier: str, feature: str) -> bool:
    return get_plan(plan_tier).get("features", {}).get(feature, False)


def plan_limit(plan_tier: str, limit_key: str) -> int:
    return int(get_plan(plan_tier).get(limit_key, 0))
