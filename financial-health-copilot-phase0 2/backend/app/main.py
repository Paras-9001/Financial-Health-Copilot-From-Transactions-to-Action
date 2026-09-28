from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.core import config
from app.core.database import get_db
from app.core.errors import install_error_handlers
from app.users.router import router as users_router

settings = config.get_settings()
app = FastAPI(
    title="Financial Health Copilot",
    version="0.1.0",
    description="Financial Health Copilot API: grounded conversational AI over deterministic financial tools.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
install_error_handlers(app)
app.include_router(auth_router, prefix=config.API_PREFIX)
app.include_router(users_router, prefix=config.API_PREFIX)
app.include_router(chat_router, prefix=config.API_PREFIX)


@app.get("/health", tags=["Operations"])
def health():
    return {"status": "ok", "phase": 5}


@app.get("/ready", tags=["Operations"])
def ready(db: Session = Depends(get_db)):
    try:
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        db.execute(text("SELECT id FROM users LIMIT 0"))
        if revision != "0002_chat_schema":
            return JSONResponse(status_code=503, content={"status": "not_ready"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
