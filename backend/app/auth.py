"""Authentication endpoints and the current-user dependency.

Register / login return a short-lived JWT access token; the frontend sends it
back as `Authorization: Bearer <token>`. get_current_user is the dependency that
protects the document/Q&A endpoints.
"""
import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from .security import create_access_token, decode_token, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

# tokenUrl points at our JSON login route — it powers Swagger's Authorize button
# and tells FastAPI where the Bearer token comes from. auto_error=False so we
# raise our own consistent 401 (instead of FastAPI's default).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Resolve the User from the Bearer token, or raise 401."""
    if not token:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise _CREDENTIALS_EXC
    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    return user


@router.post("/register", response_model=TokenResponse, status_code=201, summary="Create an account")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered user %d (%s)", user.id, user.email)
    return TokenResponse(access_token=create_access_token(str(user.id)), user=user)


@router.post("/login", response_model=TokenResponse, summary="Log in")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    user = db.query(User).filter(User.email == email).first()
    # One generic message + a dummy-hash compare on miss -> no user enumeration.
    if not verify_password(req.password, user.password_hash if user else None):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return TokenResponse(access_token=create_access_token(str(user.id)), user=user)


@router.get("/me", response_model=UserOut, summary="The current user")
def me(user: User = Depends(get_current_user)):
    return user
