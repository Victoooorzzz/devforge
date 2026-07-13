from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def summarize_files(records: Iterable[Any]) -> dict[str, Any]:
    items = list(records)
    completed = [item for item in items if _get(item, "status") in {"complete", "completed"}]
    errored = [item for item in items if _get(item, "status") in {"error", "failed"}]
    rows_saved = sum(
        max(0, int(_number(_get(item, "rows_original")) - _number(_get(item, "rows_clean"))))
        for item in completed
    )
    duplicates_removed = sum(int(_number(_get(item, "duplicates_removed"))) for item in completed)
    empty_removed = sum(int(_number(_get(item, "empty_removed"))) for item in completed)
    whitespace_fixed = sum(int(_number(_get(item, "whitespace_fixed"))) for item in completed)
    review_completed = 0
    for item in completed:
        raw_report = _get(item, "report_json", "{}") or "{}"
        try:
            report = raw_report if isinstance(raw_report, dict) else json.loads(raw_report)
        except (TypeError, ValueError, json.JSONDecodeError):
            report = {}
        invalid_rows = int(_number(report.get("schema_validation", {}).get("invalid_rows")))
        anomaly_flags = int(_number(report.get("anomaly_detection", {}).get("total_flags")))
        if invalid_rows or anomaly_flags:
            review_completed += 1

    return {
        "total_files": len(items),
        "completed_files": len(completed),
        "error_files": len(errored),
        "rows_saved": rows_saved,
        "duplicates_removed": duplicates_removed,
        "empty_removed": empty_removed,
        "whitespace_fixed": whitespace_fixed,
        "quality_actions": duplicates_removed + empty_removed + whitespace_fixed,
        "needs_review_files": len(errored) + review_completed,
    }


def summarize_invoices(invoices: Iterable[Any], *, today: date | None = None) -> dict[str, Any]:
    items = list(invoices)
    current_day = today or date.today()
    pending = [item for item in items if _get(item, "status") != "paid"]
    overdue = [
        item for item in pending
        if (_get(item, "status") == "overdue") or ((_date(_get(item, "due_date")) or current_day) < current_day)
    ]
    promised = [item for item in pending if bool(_get(item, "cron_paused")) or bool(_get(item, "payment_promise_date"))]
    promised_overdue = [item for item in overdue if item in promised]

    pending_amount = round(sum(_number(_get(item, "amount")) for item in pending), 2)
    overdue_amount = round(sum(_number(_get(item, "amount")) for item in overdue), 2)
    promised_amount = round(sum(_number(_get(item, "amount")) for item in promised), 2)

    return {
        "total_invoices": len(items),
        "paid_count": len(items) - len(pending),
        "pending_count": len(pending),
        "overdue_count": len(overdue),
        "promised_count": len(promised),
        "pending_amount": pending_amount,
        "overdue_amount": overdue_amount,
        "promised_amount": promised_amount,
        "cash_at_risk": round(
            max(overdue_amount - sum(_number(_get(item, "amount")) for item in promised_overdue), 0),
            2,
        ),
    }


def summarize_trackers(trackers: Iterable[Any]) -> dict[str, Any]:
    items = list(trackers)
    active = [item for item in items if _get(item, "status", "active") == "active"]
    price_drop_count = 0
    out_of_stock_count = 0
    potential_savings = 0.0

    for item in active:
        current = _get(item, "current_price")
        previous = _get(item, "previous_price")
        minimum = _get(item, "min_price")
        if current is not None and previous is not None and _number(current) < _number(previous):
            price_drop_count += 1
        if _get(item, "in_stock") is False:
            out_of_stock_count += 1
        if current is not None and minimum is not None and _number(current) > _number(minimum):
            potential_savings += _number(current) - _number(minimum)

    return {
        "total_trackers": len(items),
        "active_trackers": len(active),
        "price_drop_count": price_drop_count,
        "out_of_stock_count": out_of_stock_count,
        "potential_savings": round(potential_savings, 2),
    }


def build_tracker_health(trackers: Iterable[Any], *, now: datetime | None = None) -> list[dict[str, Any]]:
    current_time = now or _utc_now()
    results: list[dict[str, Any]] = []

    for item in trackers:
        tracker_id = _get(item, "id")
        label = _get(item, "label") or _get(item, "url") or f"Tracker {tracker_id}"
        last_checked = _datetime(_get(item, "last_checked"))
        frequency_hours = int(_number(_get(item, "check_frequency_hours", 24)) or 24)
        stale_after_hours = max(frequency_hours * 2, 24)
        current_price = _get(item, "current_price")
        in_stock = _get(item, "in_stock")
        status = str(_get(item, "status", "active") or "active")

        health = "healthy"
        severity = "ok"
        detail = "Tracker is checking successfully."

        if status == "blocked":
            health = "blocked"
            severity = "critical"
            detail = "The store returned an anti-bot, access-denied, or CAPTCHA challenge."
        elif status == "needs_selector":
            health = "needs_selector"
            severity = "warning"
            detail = "Static HTML did not expose a reliable price; add a CSS selector or use a different product URL."
        elif last_checked is None:
            health = "never_checked"
            severity = "critical"
            detail = "Tracker has not completed an initial scrape."
        elif current_time - last_checked > timedelta(hours=stale_after_hours):
            health = "stale"
            severity = "warning"
            detail = f"No successful check in more than {stale_after_hours} hours."
        elif current_price is None:
            health = "price_missing"
            severity = "critical"
            detail = "Last scrape did not return a usable price."
        elif in_stock is False:
            health = "out_of_stock"
            severity = "warning"
            detail = "Product is currently reported out of stock."

        results.append({
            "id": tracker_id,
            "label": label,
            "health": health,
            "severity": severity,
            "detail": detail,
            "last_checked": last_checked.isoformat() if last_checked else None,
            "check_frequency_hours": frequency_hours,
        })

    severity_order = {"critical": 0, "warning": 1, "ok": 2}
    return sorted(results, key=lambda row: (severity_order.get(row["severity"], 3), str(row["label"]).lower()))


def summarize_webhooks(requests: Iterable[Any], *, now: datetime | None = None) -> dict[str, Any]:
    items = list(requests)
    current_time = now or _utc_now()
    recent_cutoff = current_time - timedelta(hours=24)
    recent_24h = 0
    retry_pressure = 0
    failed_forwards = 0
    auto_retry_enabled = 0

    for item in items:
        received_at = _datetime(_get(item, "received_at"))
        if received_at and received_at >= recent_cutoff:
            recent_24h += 1
        retry_pressure += int(_number(_get(item, "retry_count")))
        status = _get(item, "last_retry_status")
        if status is not None and int(_number(status)) >= 400:
            failed_forwards += 1
        if bool(_get(item, "auto_retry_enabled")):
            auto_retry_enabled += 1

    return {
        "total_requests": len(items),
        "recent_24h": recent_24h,
        "retry_pressure": retry_pressure,
        "failed_forwards": failed_forwards,
        "auto_retry_enabled": auto_retry_enabled,
    }


def summarize_feedback(entries: Iterable[Any]) -> dict[str, Any]:
    items = list(entries)
    sentiments = {"positive": 0, "negative": 0, "neutral": 0}
    themes: list[str] = []
    urgent_count = 0

    for item in items:
        sentiment = _get(item, "sentiment")
        if sentiment in sentiments:
            sentiments[sentiment] += 1
        if bool(_get(item, "is_urgent")):
            urgent_count += 1

        raw_themes = _get(item, "themes")
        if raw_themes is None:
            raw_themes = _get(item, "themes_json")
            if isinstance(raw_themes, str):
                try:
                    raw_themes = json.loads(raw_themes)
                except json.JSONDecodeError:
                    raw_themes = []
        if isinstance(raw_themes, list):
            themes.extend(str(theme) for theme in raw_themes if theme)

    return {
        "total": len(items),
        "urgent_count": urgent_count,
        "sentiment_stats": sentiments,
        "top_themes": [theme for theme, _ in Counter(themes).most_common(5)],
    }
