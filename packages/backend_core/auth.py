# packages/backend-core/auth.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select

from .config import get_settings
from .database import get_session

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# --- Models ---

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: Optional[str] = Field(default=None)
    hashed_password: str
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    lemonsqueezy_customer_id: Optional[str] = Field(default=None, index=True)

    is_active: bool = Field(default=False)
    trial_ends_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_on_trial(self) -> bool:
        """True if the user has an active free trial (not yet expired)."""
        if self.trial_ends_at is None:
            return False
        return datetime.now(timezone.utc) < self.trial_ends_at

    @property
    def has_access(self) -> bool:
        """True if the user has a paid subscription OR an active trial."""
        return self.is_active or self.is_on_trial


# --- Schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
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
    is_on_trial: bool
    has_access: bool
    has_active_subscription: bool
    trial_ends_at: Optional[datetime]
    created_at: datetime
    lemonsqueezy_customer_id: Optional[str]

# --- Password Utilities ---

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# --- JWT Utilities ---

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
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

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    payload = verify_token(credentials.credentials)
    user_id = int(payload["sub"])

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# --- Router ---

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@auth_router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return ProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_on_trial=user.is_on_trial,
        has_access=user.has_access,
        has_active_subscription=user.is_active,
        trial_ends_at=user.trial_ends_at,
        created_at=user.created_at,
        lemonsqueezy_customer_id=user.lemonsqueezy_customer_id,
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

    return ProfileResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_on_trial=user.is_on_trial,
        has_access=user.has_access,
        has_active_subscription=user.is_active,
        trial_ends_at=user.trial_ends_at,
        created_at=user.created_at,
        lemonsqueezy_customer_id=user.lemonsqueezy_customer_id,
    )
