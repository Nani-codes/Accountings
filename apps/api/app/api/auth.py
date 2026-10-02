import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas.auth import (
    GoogleAuthRequest,
    LoginRequest,
    OrganizationOut,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        name=user.name,
        organization=OrganizationOut(
            id=str(user.organization.id),
            name=user.organization.name,
        ),
    )


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, token = auth_service.signup(
        db,
        email=body.email,
        password=body.password,
        name=body.name,
        firm_name=body.firm_name,
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, token = auth_service.login(db, email=body.email, password=body.password)
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google auth not configured")
    # Verify via Google tokeninfo (simple v1; swap to google-auth lib later if needed)
    resp = httpx.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": body.id_token},
        timeout=10.0,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    data = resp.json()
    if data.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="Invalid Google audience")
    email = data.get("email")
    sub = data.get("sub")
    name = data.get("name") or (email.split("@")[0] if email else "User")
    if not email or not sub:
        raise HTTPException(status_code=401, detail="Google token missing claims")
    _, token = auth_service.google_login_or_signup(
        db, google_sub=sub, email=email, name=name
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(auth_service.get_current_user)) -> UserOut:
    return _user_out(user)
