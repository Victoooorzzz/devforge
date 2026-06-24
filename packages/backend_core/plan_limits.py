from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .auth import User
from .product_access import UserProductAccess
from .product_catalog import normalize_app_slug

PlanName = Literal["trial", "paid"]


@dataclass(frozen=True)
class PriceTrackrLimits:
    max_active_trackers: int
    min_check_frequency_hours: int


@dataclass(frozen=True)
class WebhookMonitorLimits:
    max_endpoints: int
    events_per_day: int
    retention_days: int
    replay_enabled: bool
    diff_enabled: bool
    search_enabled: bool


@dataclass(frozen=True)
class InvoiceFollowLimits:
    max_active_invoices: int
    monthly_emails: int
    monthly_nlp: int
    max_payment_connections: int
    max_users: int
    api_access: bool
    history_retention_days: int
    payment_connections_enabled: bool
    weekly_digest_enabled: bool


@dataclass(frozen=True)
class FeedbackLensLimits:
    max_feedback_per_month: int
    max_sources: int
    allowed_sources: frozenset[str]
    github_issue_enabled: bool
    weekly_digest_enabled: bool
    history_retention_days: int


PRICETRACKR_LIMITS: dict[PlanName, PriceTrackrLimits] = {
    "trial": PriceTrackrLimits(max_active_trackers=5, min_check_frequency_hours=24),
    "paid": PriceTrackrLimits(max_active_trackers=100, min_check_frequency_hours=1),
}

WEBHOOKMONITOR_LIMITS: dict[PlanName, WebhookMonitorLimits] = {
    "trial": WebhookMonitorLimits(
        max_endpoints=1,
        events_per_day=100,
        retention_days=7,
        replay_enabled=False,
        diff_enabled=False,
        search_enabled=False,
    ),
    "paid": WebhookMonitorLimits(
        max_endpoints=10,
        events_per_day=10_000,
        retention_days=30,
        replay_enabled=True,
        diff_enabled=True,
        search_enabled=True,
    ),
}


FEEDBACKLENS_LIMITS: dict[str, FeedbackLensLimits] = {
    "free": FeedbackLensLimits(
        max_feedback_per_month=100,
        max_sources=2,
        allowed_sources=frozenset({"manual", "email"}),
        github_issue_enabled=False,
        weekly_digest_enabled=False,
        history_retention_days=30,
    ),
    "pro": FeedbackLensLimits(
        max_feedback_per_month=5_000,
        max_sources=10,
        allowed_sources=frozenset({"manual", "email", "github", "canny", "twitter", "reddit"}),
        github_issue_enabled=True,
        weekly_digest_enabled=True,
        history_retention_days=180,
    ),
    "team": FeedbackLensLimits(
        max_feedback_per_month=25_000,
        max_sources=50,
        allowed_sources=frozenset({"manual", "email", "github", "canny", "twitter", "reddit"}),
        github_issue_enabled=True,
        weekly_digest_enabled=True,
        history_retention_days=365,
    ),
}


INVOICEFOLLOW_LIMITS: dict[str, InvoiceFollowLimits] = {
    "free": InvoiceFollowLimits(
        max_active_invoices=5,
        monthly_emails=25,
        monthly_nlp=10,
        max_payment_connections=0,
        max_users=1,
        api_access=False,
        history_retention_days=30,
        payment_connections_enabled=False,
        weekly_digest_enabled=False,
    ),
    "pro": InvoiceFollowLimits(
        max_active_invoices=50,
        monthly_emails=500,
        monthly_nlp=200,
        max_payment_connections=2,
        max_users=1,
        api_access=True,
        history_retention_days=90,
        payment_connections_enabled=True,
        weekly_digest_enabled=True,
    ),
    "team": InvoiceFollowLimits(
        max_active_invoices=200,
        monthly_emails=2000,
        monthly_nlp=1000,
        max_payment_connections=10,
        max_users=5,
        api_access=True,
        history_retention_days=365,
        payment_connections_enabled=True,
        weekly_digest_enabled=True,
    ),
}


def _plan_label(plan: PlanName) -> str:
    return "Trial" if plan == "trial" else "Paid"


async def resolve_user_plan(user: User, session: AsyncSession, app_name: str) -> PlanName:
    app_slug = normalize_app_slug(app_name)
    if app_slug:
        access_result = await session.execute(
            select(UserProductAccess).where(
                UserProductAccess.user_id == user.id,
                UserProductAccess.app_name == app_slug,
                UserProductAccess.is_active == True,  # noqa: E712
            )
        )
        if access_result.scalar_one_or_none() is not None:
            return "paid"

    if not app_slug and user.is_active:
        return "paid"

    return "trial"


async def resolve_user_plan_by_id(session: AsyncSession, user_id: int, app_name: str) -> PlanName:
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        return "trial"
    return await resolve_user_plan(user, session, app_name)


async def get_pricetrackr_limits(user: User, session: AsyncSession) -> tuple[PlanName, PriceTrackrLimits]:
    plan = await resolve_user_plan(user, session, "pricetrackr")
    return plan, PRICETRACKR_LIMITS[plan]


async def get_webhookmonitor_limits_for_user_id(
    session: AsyncSession,
    user_id: int,
) -> tuple[PlanName, WebhookMonitorLimits]:
    plan = await resolve_user_plan_by_id(session, user_id, "webhookmonitor")
    return plan, WEBHOOKMONITOR_LIMITS[plan]


async def get_invoicefollow_limits(user: User, session: AsyncSession) -> tuple[str, InvoiceFollowLimits]:
    plan = "pro" if await resolve_user_plan(user, session, "invoicefollow") == "paid" else "free"
    return plan, INVOICEFOLLOW_LIMITS[plan]


def get_feedbacklens_limits(user: User) -> tuple[str, FeedbackLensLimits]:
    plan = "pro" if user.is_active else "free"
    return plan, FEEDBACKLENS_LIMITS[plan]


def reject_price_frequency_if_needed(plan: PlanName, limits: PriceTrackrLimits, requested_hours: int) -> None:
    if requested_hours < limits.min_check_frequency_hours:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"{_plan_label(plan)} plan allows price checks every "
                f"{limits.min_check_frequency_hours} hours or slower."
            ),
        )


def reject_tracker_count_if_needed(plan: PlanName, limits: PriceTrackrLimits, active_count: int) -> None:
    if active_count >= limits.max_active_trackers:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"{_plan_label(plan)} plan is limited to "
                f"{limits.max_active_trackers} active trackers."
            ),
        )


def reject_webhook_rate_if_needed(plan: PlanName, limits: WebhookMonitorLimits, recent_count: int) -> None:
    if recent_count >= limits.events_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"{_plan_label(plan)} plan is limited to "
                f"{limits.events_per_day} events per day."
            ),
        )


def reject_webhook_endpoint_count_if_needed(plan: PlanName, limits: WebhookMonitorLimits, endpoint_count: int) -> None:
    if endpoint_count >= limits.max_endpoints:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"{_plan_label(plan)} plan is limited to "
                f"{limits.max_endpoints} webhook endpoint{'s' if limits.max_endpoints != 1 else ''}."
            ),
        )


def reject_feedbacklens_source_if_needed(plan: str, limits: FeedbackLensLimits, source_type: str, source_count: int) -> None:
    label = plan.title()
    if source_type not in limits.allowed_sources:
        allowed = ", ".join(sorted(limits.allowed_sources))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{label} plan supports only these FeedbackLens sources: {allowed}.",
        )
    if source_count >= limits.max_sources:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{label} plan is limited to {limits.max_sources} FeedbackLens sources.",
        )


def reject_feedbacklens_feedback_count_if_needed(
    plan: str,
    limits: FeedbackLensLimits,
    monthly_count: int,
    incoming_count: int = 1,
) -> None:
    if monthly_count + incoming_count > limits.max_feedback_per_month:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"{plan.title()} plan is limited to "
                f"{limits.max_feedback_per_month} FeedbackLens items per month."
            ),
        )
