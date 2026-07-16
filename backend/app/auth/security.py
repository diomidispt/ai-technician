"""Password hashing (bcrypt) and JWT sign/verify.

Local simulation of Cognito's token issuance. In AWS this is replaced by Cognito + an API
Gateway authorizer; the rest of the app (route guards reading a role) stays the same.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(*, user_id: int, email: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Return the JWT claims, or raise jwt.PyJWTError if invalid/expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
