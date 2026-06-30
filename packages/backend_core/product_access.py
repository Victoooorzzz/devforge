from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import UniqueConstraint, func, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select

from .auth import User, get_current_user
from .database import get_session
from .product_catalog import normalize_app_slug


class UserProductAccess(SQLModel, table=True):
    __tablename__ = "user_product_access"
    __table_args__ = (
        UniqueConstraint("user_id", "app_name", name="uq_user_product_access_user_app"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    app_name: str = Field(index=True, max_length=50)
    polar_product_id: Optional[str] = Field(default=None, index=True)
    is_active: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


async def user_has_product_access(user: User, app_name: str, session: AsyncSession) -> bool:
    app_slug = normalize_app_slug(app_name)
    if not app_slug:
        return False
    # Every authenticated user has base Free access. Paid product rows only
    # upgrade limits/features to Pro or Team.
    return True


def require_product_access(app_name: str):
    async def dependency(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if await user_has_product_access(user, app_name, session):
            return user
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Authenticated Free, Pro, or Team access required for this product.",
        )

    return dependency


async def set_user_product_access(
    *,
    session: AsyncSession,
    user: User,
    app_name: str,
    polar_product_id: str | None,
    is_active: bool,
) -> None:
    app_slug = normalize_app_slug(app_name)
    if not app_slug:
        return

    result = await session.execute(
        select(UserProductAccess).where(
            UserProductAccess.user_id == user.id,
            UserProductAccess.app_name == app_slug,
        )
    )
    access = result.scalar_one_or_none()
    if not access:
        access = UserProductAccess(user_id=user.id, app_name=app_slug)

    access.polar_product_id = polar_product_id
    access.is_active = is_active
    access.updated_at = datetime.utcnow()
    session.add(access)

    other_active_count_result = await session.execute(
        sa_select(func.count(UserProductAccess.id)).where(
            UserProductAccess.user_id == user.id,
            UserProductAccess.app_name != app_slug,
            UserProductAccess.is_active == True,  # noqa: E712
        )
    )
    other_active_count = other_active_count_result.scalar_one()
    user.is_active = is_active or other_active_count > 0
    if is_active:
        user.trial_ends_at = None
    session.add(user)
