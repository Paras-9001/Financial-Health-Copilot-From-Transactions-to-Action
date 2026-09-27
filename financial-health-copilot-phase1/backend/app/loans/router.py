from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.accounts.repository import AccountRepository
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User
from app.loans.repository import LoanRepository
from app.loans.schemas import LoanCreate, LoanListResponse, LoanResponse

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.get("", response_model=LoanListResponse)
def list_loans(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"loans": LoanRepository(db).list_for_user(user.id)}


@router.post("", response_model=LoanResponse, status_code=201)
def create_loan(data: LoanCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.account_id:
        account = AccountRepository(db).get_owned(user.id, data.account_id)
        if account is None:
            raise APIError(404, "account_not_found", "Account was not found.")
        if account.type != "loan":
            raise APIError(422, "invalid_type", "The linked account must have type 'loan'.")
    loan = LoanRepository(db).create(user.id, **data.model_dump())
    db.commit()
    db.refresh(loan)
    return loan
