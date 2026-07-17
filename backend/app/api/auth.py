"""Login + who-am-I. Local simulation of Cognito sign-in."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_session

router = APIRouter()

MIN_PASSWORD_LENGTH = 6


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    email: str
    role: str
    must_change_password: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == body.email.strip().lower()))
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
    )
    if user is None or not verify_password(body.password, user.password_hash):
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    if user.access_expires is not None and datetime.now(UTC) > user.access_expires:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access expired")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            email=user.email, role=user.role, must_change_password=user.must_change_password
        ),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(email=user.email, role=user.role, must_change_password=user.must_change_password)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """Self-service password change. Also clears any forced-reset flag (Cognito parity)."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    if len(body.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"New password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )
    # Re-load in this session to persist the change.
    db_user = session.get(User, user.id)
    db_user.password_hash = hash_password(body.new_password)
    db_user.must_change_password = False
    session.commit()
