# packages/backend-core/auth.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select

import random
from .config import get_settings
from .email_service import send_email
from .database import get_session
from .product_catalog import app_slug_from_url, normalize_plan_slug, resolve_product_id_for_app

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# --- Models ---

class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: Optional[str] = Field(default=None)
    hashed_password: str
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    lemonsqueezy_customer_id: Optional[str] = Field(default=None, index=True)

    is_active: bool = Field(default=False)
    is_email_verified: bool = Field(default=False)
    verification_code: Optional[str] = Field(default=None)
    trial_ends_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_on_trial(self) -> bool:
        """True if the user has an active free trial (not yet expired)."""
        if self.trial_ends_at is None:
            return False
        
        now = datetime.utcnow()
        trial_end = self.trial_ends_at
        if trial_end.tzinfo is not None:
            now = now.replace(tzinfo=timezone.utc)
            
        return now < trial_end

    @property
    def has_access(self) -> bool:
        """True if the user has a paid subscription OR an active trial."""
        if self.is_active:
            return True
        return self.is_on_trial

    def check_access(self):
        if not self.has_access:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Your 7-day trial has expired. Please subscribe to continue using DevForge.",
            )


# --- Schemas ---

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password: str
    app_name: Optional[str] = None # filecleaner, invoicefollow, etc.
    plan: Optional[str] = "pro"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    is_email_verified: bool = False
    checkout_url: Optional[str] = None


class VerifyRequest(BaseModel):
    code: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_email_verified: bool
    is_on_trial: bool
    has_access: bool
    trial_ends_at: Optional[datetime]
    created_at: datetime

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class ProfileResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_active: bool
    is_email_verified: bool
    is_on_trial: bool
    has_access: bool
    has_active_subscription: bool
    trial_ends_at: Optional[datetime]
    created_at: datetime
    lemonsqueezy_customer_id: Optional[str]
    active_products: list[str] = Field(default_factory=list)
    plans_by_product: dict[str, str] = Field(default_factory=dict)
    dashboard_limits_by_product: dict[str, dict[str, dict[str, int | float]]] = Field(default_factory=dict)

# --- Password Utilities ---

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# --- JWT Utilities ---

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# --- Dependencies ---

def set_auth_cookies(response: Response, token: str):
    response.set_cookie(
        key="devforge_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=30 * 24 * 60 * 60,
        path="/"
    )
    response.set_cookie(
        key="devforge_auth_status",
        value="true",
        httponly=False,
        secure=True,
        samesite="none",
        max_age=30 * 24 * 60 * 60,
        path="/"
    )

def clear_auth_cookies(response: Response):
    response.delete_cookie("devforge_token", path="/", secure=True, samesite="none")
    response.delete_cookie("devforge_auth_status", path="/", secure=True, samesite="none")

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get("devforge_token")
    if not token:
        # Fallback to Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
        
    payload = verify_token(token)
    user_id = int(payload["sub"])

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def require_user_access(user: User = Depends(get_current_user)) -> User:
    user.check_access()
    return user


# --- Router ---

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, background_tasks: BackgroundTasks, response: Response, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Generate verification code
    v_code = str(random.randint(100000, 999999))
    
    user = User(
        name=body.name.strip() if body.name and body.name.strip() else None,
        email=body.email,
        hashed_password=hash_password(body.password),
        is_active=False,
        is_email_verified=False,
        verification_code=v_code,
        trial_ends_at=datetime.utcnow() + timedelta(days=7)
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    await session.commit()

    # Send verification email in background
    background_tasks.add_task(
        send_email,
        to=user.email,
        subject="Verifica tu cuenta en DevForge",
        html_body=f"""
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #6366f1; border-radius: 12px;">
            <h2 style="color: #4338ca;">Bienvenido a DevForge</h2>
            <p>Tu código de verificación es:</p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #6366f1; margin: 20px 0;">
                {v_code}
            </div>
            <p>Ingresa este código en la aplicación para activar tu cuenta.</p>
        </div>
        """
    )

    token = create_access_token(user.id, user.email)
    
    # Generate checkout URL if app_name is provided
    checkout_url = None
    if body.app_name:
        from .polar_handler import create_polar_checkout
        product_id = resolve_product_id_for_app(settings, body.app_name, normalize_plan_slug(body.plan))
        
        if product_id:
            try:
                checkout_url = await create_polar_checkout(user.id, user.email, product_id)
            except Exception as e:
                print(f"Error creating checkout URL: {e}")

    set_auth_cookies(response, token)
    
    return TokenResponse(
        access_token=token,
        is_email_verified=False,
        checkout_url=checkout_url
    )


@auth_router.post("/verify", response_model=TokenResponse)
async def verify_email(body: VerifyRequest, response: Response, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if user.verification_code != body.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de verificación incorrecto",
        )
    
    user.is_email_verified = True
    user.verification_code = None
    session.add(user)
    await session.commit()
    
    token = create_access_token(user.id, user.email)
    set_auth_cookies(response, token)
    return TokenResponse(access_token=token, is_email_verified=True)


@auth_router.post("/resend-code")
async def resend_verification_code(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Generates a new verification code and resends the verification email."""
    if user.is_email_verified:
        raise HTTPException(status_code=400, detail="Account is already verified")

    v_code = str(random.randint(100000, 999999))
    user.verification_code = v_code
    session.add(user)
    await session.commit()

    background_tasks.add_task(
        send_email,
        to=user.email,
        subject="Tu nuevo código de verificación — DevForge",
        html_body=f"""
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #6366f1; border-radius: 12px;">
            <h2 style="color: #4338ca;">Nuevo código de verificación</h2>
            <p>Tu nuevo código es:</p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #6366f1; margin: 20px 0;">
                {v_code}
            </div>
            <p>Este código expira en 30 minutos.</p>
        </div>
        """
    )
    return {"success": True}


@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.email)
    set_auth_cookies(response, token)
    return TokenResponse(
        access_token=token,
        is_email_verified=user.is_email_verified
    )

@auth_router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"success": True}


@auth_router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from .product_access import UserProductAccess
    from .plan_limits import build_dashboard_limits_by_product, resolve_user_plan

    result = await session.execute(
        select(UserProductAccess).where(
            UserProductAccess.user_id == user.id,
            UserProductAccess.is_active == True,  # noqa: E712
        )
    )
    active_products = [p.app_name for p in result.scalars().all()]
    plans_by_product = {
        app_name: await resolve_user_plan(user, session, app_name)
        for app_name in ["filecleaner", "invoicefollow", "pricetrackr", "webhookmonitor", "feedbacklens"]
    }
    request_app = app_slug_from_url(request.headers.get("origin")) or app_slug_from_url(request.headers.get("referer"))
    has_active_subscription = (
        request_app in active_products
        if request_app
        else user.is_active or bool(active_products)
    )
    has_access = user.is_on_trial or has_active_subscription
    return ProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        is_on_trial=user.is_on_trial,
        has_access=has_access,
        has_active_subscription=has_active_subscription,
        trial_ends_at=user.trial_ends_at,
        created_at=user.created_at,
        lemonsqueezy_customer_id=user.lemonsqueezy_customer_id,
        active_products=active_products,
        plans_by_product=plans_by_product,
        dashboard_limits_by_product=build_dashboard_limits_by_product(),
    )

@auth_router.put("/profile", response_model=ProfileResponse)
async def update_profile(body: ProfileUpdateRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if body.email and body.email != user.email:
        existing = await session.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user.email = body.email

    if body.name is not None:
        user.name = body.name

    session.add(user)
    await session.flush()
    await session.refresh(user)
    await session.commit()

    from .product_access import UserProductAccess
    from .plan_limits import build_dashboard_limits_by_product, resolve_user_plan
    active_result = await session.execute(
        select(UserProductAccess).where(
            UserProductAccess.user_id == user.id,
            UserProductAccess.is_active == True,  # noqa: E712
        )
    )
    active_products = [p.app_name for p in active_result.scalars().all()]
    plans_by_product = {
        app_name: await resolve_user_plan(user, session, app_name)
        for app_name in ["filecleaner", "invoicefollow", "pricetrackr", "webhookmonitor", "feedbacklens"]
    }

    has_active_subscription = user.is_active or bool(active_products)
    has_access = user.is_on_trial or has_active_subscription

    return ProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        is_on_trial=user.is_on_trial,
        has_access=has_access,
        has_active_subscription=has_active_subscription,
        trial_ends_at=user.trial_ends_at,
        created_at=user.created_at,
        lemonsqueezy_customer_id=user.lemonsqueezy_customer_id,
        active_products=active_products,
        plans_by_product=plans_by_product,
        dashboard_limits_by_product=build_dashboard_limits_by_product(),
    )
