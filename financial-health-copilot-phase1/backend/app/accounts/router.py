from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.accounts.repository import AccountRepository
from app.accounts.schemas import AccountCreate, AccountListResponse, AccountResponse
from app.core.database import get_db
from app.core.security import current_user
from app.db.user import User

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=AccountListResponse)
def list_accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"accounts": AccountRepository(db).list_for_user(user.id)}


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(data: AccountCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    account = AccountRepository(db).create(user.id, **data.model_dump())
    db.commit()
    db.refresh(account)
    return account
