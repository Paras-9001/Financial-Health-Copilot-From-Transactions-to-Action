from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user
from app.db.user import User
from app.income_sources.repository import IncomeSourceRepository
from app.income_sources.schemas import (
    IncomeSourceCreate,
    IncomeSourceListResponse,
    IncomeSourceResponse,
)

router = APIRouter(prefix="/income-sources", tags=["Income Sources"])


@router.get("", response_model=IncomeSourceListResponse)
def list_income_sources(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"income_sources": IncomeSourceRepository(db).list_for_user(user.id)}


@router.post("", response_model=IncomeSourceResponse, status_code=201)
def create_income_source(
    data: IncomeSourceCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    source = IncomeSourceRepository(db).create(user.id, **data.model_dump())
    db.commit()
    db.refresh(source)
    return source
