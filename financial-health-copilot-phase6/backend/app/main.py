from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.accounts.router import router as accounts_router
from app.analytics.router import router as analytics_router
from app.auth.router import router as auth_router
from app.categories.router import router as categories_router
from app.chat.router import router as chat_router
from app.core import config
from app.core.database import get_db
from app.core.errors import install_error_handlers
from app.credit_cards.router import router as credit_cards_router
from app.csv_import.router import router as csv_import_router
from app.forecast.router import router as forecast_router
from app.income_sources.router import router as income_sources_router
from app.loans.router import router as loans_router
from app.onboarding.router import router as onboarding_router
from app.recommendations.router import router as recommendations_router
from app.recurring.router import router as recurring_router
from app.risks.router import router as risks_router
from app.simulation.router import router as simulation_router
from app.transactions.router import router as transactions_router
from app.users.router import router as users_router

settings = config.get_settings()
app = FastAPI(
    title="Financial Health Copilot",
    version="0.7.0",
    description="Phase 6: Complete responsive frontend over the deterministic Phase 1–5 API.",
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
app.include_router(analytics_router, prefix=config.API_PREFIX)
app.include_router(recurring_router, prefix=config.API_PREFIX)
app.include_router(forecast_router, prefix=config.API_PREFIX)
app.include_router(risks_router, prefix=config.API_PREFIX)
app.include_router(recommendations_router, prefix=config.API_PREFIX)
app.include_router(simulation_router, prefix=config.API_PREFIX)
app.include_router(chat_router, prefix=config.API_PREFIX)


@app.get("/health", tags=["Operations"])
def health():
    return {"status": "ok", "phase": 6}


@app.get("/ready", tags=["Operations"])
def ready(db: Session = Depends(get_db)):
    try:
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        db.execute(text("SELECT id FROM users LIMIT 0"))
        if revision != "0004_phase5":
            return JSONResponse(status_code=503, content={"status": "not_ready"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
