# packages/backend-core/__init__.py

from .auth import (
    User,
    auth_router,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from .product_access import require_product_access, user_has_product_access
from .config import Settings, get_settings
from .database import create_db_and_tables, get_session, get_managed_session
from .email_service import send_email
from .main_factory import create_app
from . import scraper
