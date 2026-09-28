from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User
from app.onboarding.personas import PERSONAS
from app.onboarding.schemas import DemoSeedRequest, DemoSeedResponse, PersonaResponse
from app.onboarding.service import has_financial_data, seed_persona

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/personas", response_model=list[PersonaResponse])
def list_personas(_user: User = Depends(current_user)):
    return [
        {"key": key, "name": value["display_name"], "description": value["description"]}
        for key, value in PERSONAS.items()
    ]


@router.post("/demo", response_model=DemoSeedResponse, status_code=201)
def choose_demo_persona(
    data: DemoSeedRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if has_financial_data(db, user.id):
        raise APIError(
            409,
            "onboarding_already_completed",
            "This account already has financial data. Use a fresh account to choose another persona.",
        )
    return seed_persona(db, user.id, data.persona)
