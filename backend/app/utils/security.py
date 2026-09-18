"""Authentication helpers.

Deliberately simple demo auth (spec section 12):
  * admin routes   -> ``Authorization: Bearer <ADMIN_TOKEN>``
  * webhook route  -> ``X-Webhook-Secret: <WEBHOOK_SECRET>``

Both use hmac.compare_digest (constant-time comparison) so an attacker
cannot measure response time to guess the secret one character at a time.
"""
import hmac

from fastapi import Header

from app.config import settings
from app.utils.errors import AuthError


def require_admin(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency: pass only with a valid admin Bearer token.

    Missing or wrong token -> 401 (unauthenticated). We do not model
    separate roles, so 403 (authenticated but not allowed) never fires here;
    the docs explain where it *would* go.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthError("missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, settings.admin_token):
        raise AuthError("invalid admin token")


def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None)) -> None:
    """FastAPI dependency: pass only with the shared webhook secret."""
    if x_webhook_secret is None:
        raise AuthError("missing X-Webhook-Secret header")
    if not hmac.compare_digest(x_webhook_secret, settings.webhook_secret):
        raise AuthError("invalid webhook secret")
