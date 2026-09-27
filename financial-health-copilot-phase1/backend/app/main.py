from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.accounts.router import router as accounts_router
from app.auth.router import router as auth_router
from app.categories.router import router as categories_router
from app.core import config
from app.core.database import get_db
from app.core.errors import install_error_handlers
from app.credit_cards.router import router as credit_cards_router
from app.csv_import.router import router as csv_import_router
from app.income_sources.router import router as income_sources_router
from app.loans.router import router as loans_router
from app.onboarding.router import router as onboarding_router
from app.transactions.router import router as transactions_router
from app.users.router import router as users_router

settings = config.get_settings()
app = FastAPI(
    title="Financial Health Copilot",
    version="0.2.0",
    description="Phase 1: authenticated financial data ingestion and onboarding.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
install_error_handlers(app)
app.include_router(auth_router, prefix=config.API_PREFIX)
app.include_router(users_router, prefix=config.API_PREFIX)
app.include_router(accounts_router, prefix=config.API_PREFIX)
app.include_router(transactions_router, prefix=config.API_PREFIX)
app.include_router(categories_router, prefix=config.API_PREFIX)
app.include_router(loans_router, prefix=config.API_PREFIX)
app.include_router(credit_cards_router, prefix=config.API_PREFIX)
app.include_router(income_sources_router, prefix=config.API_PREFIX)
app.include_router(csv_import_router, prefix=config.API_PREFIX)
app.include_router(onboarding_router, prefix=config.API_PREFIX)


@app.get("/health", tags=["Operations"])
def health():
    return {"status": "ok", "phase": 1}


@app.get("/ready", tags=["Operations"])
def ready(db: Session = Depends(get_db)):
    try:
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        db.execute(text("SELECT id FROM users LIMIT 0"))
        if revision != "0002_phase1":
            return JSONResponse(status_code=503, content={"status": "not_ready"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
