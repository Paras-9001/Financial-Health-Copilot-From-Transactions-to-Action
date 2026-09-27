from fastapi import APIRouter, Depends

from app.auth.schemas import UserResponse
from app.core.security import current_user
from app.db.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(current_user)):
    return user
