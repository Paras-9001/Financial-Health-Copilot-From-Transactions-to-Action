from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.rate_limit import limit_auth
from app.auth.schemas import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import create_token, hash_password, verify_password
from app.db.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"], dependencies=[Depends(limit_auth)])


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    user = User(email=data.email, name=data.name, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise APIError(409, "email_exists", "An account with this email already exists.") from None
    db.refresh(user)
    return {"user_id": user.id, "token": create_token(user.id)}


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    verified = verify_password(data.password, user.password_hash if user else None)
    if not verified or user is None:
        raise APIError(401, "invalid_credentials", "Email or password is incorrect.")
    return {"token": create_token(user.id), "user": user}
