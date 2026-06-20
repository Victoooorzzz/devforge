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
