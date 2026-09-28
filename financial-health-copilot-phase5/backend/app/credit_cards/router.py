from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.accounts.repository import AccountRepository
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.credit_cards.repository import CreditCardRepository
from app.credit_cards.schemas import CreditCardCreate, CreditCardListResponse, CreditCardResponse
from app.db.user import User

router = APIRouter(prefix="/credit-cards", tags=["Credit Cards"])


@router.get("", response_model=CreditCardListResponse)
def list_credit_cards(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"credit_cards": CreditCardRepository(db).list_for_user(user.id)}


@router.post("", response_model=CreditCardResponse, status_code=201)
def create_credit_card(
    data: CreditCardCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    account = AccountRepository(db).get_owned(user.id, data.account_id)
    if account is None:
        raise APIError(404, "account_not_found", "Account was not found.")
    if account.type != "credit_card":
        raise APIError(422, "invalid_type", "The linked account must have type 'credit_card'.")
    repository = CreditCardRepository(db)
    if repository.get_by_account(account.id):
        raise APIError(409, "credit_card_exists", "This account already has card details.")
    card = repository.create(**data.model_dump())
    db.commit()
    db.refresh(card)
    return card
