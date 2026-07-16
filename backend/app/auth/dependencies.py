"""FastAPI auth dependencies: identify the caller and guard by role.

`get_current_user` loads the user from the DB on every request and re-checks `is_active` and
`access_expires` — so disabling a user or hitting their expiry blocks them **immediately**,
not just when their token expires. This is the local equivalent of Cognito's instant revocation.
"""

from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db.models import User
from app.db.session import get_session

_bearer = HTTPBearer(auto_error=False)
_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise _UNAUTHORIZED from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    if user.access_expires is not None and datetime.now(UTC) > user.access_expires:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access expired")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return user
