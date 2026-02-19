"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.security.jwt import create_token, hash_password, verify_password

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> TokenResponse:
    """Login or create a user and return a JWT token."""
    user = session.query(User).filter(User.username == payload.username).one_or_none()
    if user is None:
        user = User(
            username=payload.username,
            email=payload.username,
            full_name=None,
            password_hash=hash_password(payload.password),
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token)
