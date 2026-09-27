from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.categories.repository import CategoryRepository
from app.categories.schemas import CategoryListResponse
from app.core.database import get_db
from app.core.security import current_user
from app.db.user import User

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=CategoryListResponse)
def list_categories(_user: User = Depends(current_user), db: Session = Depends(get_db)):
    categories = CategoryRepository(db).list_all()
    db.commit()
    return {"categories": categories}
