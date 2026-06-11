"""Shared aggregation utilities for intelligence modules."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any


def parse_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(str(value)[:20].strip(), fmt).date()
        except ValueError:
            continue
    return None


def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def period_label(month: str) -> str:
    try:
        dt = datetime.strptime(month, "%Y-%m")
        return dt.strftime("%b %Y")
    except ValueError:
        return month


def group_by_month(
    records: list[dict[str, Any]],
    date_field: str,
    value_field: str,
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for rec in records:
        d = parse_date(rec.get(date_field))
        if not d:
            continue
        totals[month_key(d)] += float(rec.get(value_field, 0) or 0)
    return dict(sorted(totals.items()))


def growth_pct(current: float, previous: float) -> float | None:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / abs(previous) * 100, 2)


def trend_series(series: dict[str, float], periods: int = 12) -> list[dict[str, Any]]:
    items = list(series.items())[-periods:]
    return [{"period": k, "label": period_label(k), "value": round(v, 2)} for k, v in items]


def pct_change_series(series: dict[str, float]) -> list[dict[str, Any]]:
    keys = sorted(series.keys())
    result: list[dict[str, Any]] = []
    for i, key in enumerate(keys):
        if i == 0:
            result.append({"period": key, "label": period_label(key), "change_pct": 0.0})
            continue
        prev = series[keys[i - 1]]
        curr = series[key]
        result.append({
            "period": key,
            "label": period_label(key),
            "change_pct": growth_pct(curr, prev) or 0.0,
        })
    return result


def filter_vouchers_by_type(vouchers: list[dict], *keywords: str) -> list[dict]:
    result = []
    for v in vouchers:
        vch_type = (v.get("voucher_type") or "").lower()
        if any(kw in vch_type for kw in keywords):
            result.append(v)
    return result


def sum_field(records: list[dict], field: str) -> float:
    return round(sum(float(r.get(field, 0) or 0) for r in records), 2)


def top_n_by_field(
    records: list[dict],
    group_field: str,
    value_field: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for rec in records:
        key = rec.get(group_field) or "Unknown"
        totals[str(key)] += float(rec.get(value_field, 0) or 0)
    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return [
        {"name": name, "value": round(val, 2), "share_pct": 0.0}
        for name, val in sorted_items[:limit]
    ]


def apply_share_pct(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(i["value"] for i in items)
    if total <= 0:
        return items
    for item in items:
        item["share_pct"] = round(item["value"] / total * 100, 2)
    return items


def recent_period_cutoff(days: int = 90) -> date:
    return datetime.now(UTC).date() - timedelta(days=days)


def in_period(rec: dict, date_field: str, since: date) -> bool:
    d = parse_date(rec.get(date_field))
    return d is not None and d >= since
