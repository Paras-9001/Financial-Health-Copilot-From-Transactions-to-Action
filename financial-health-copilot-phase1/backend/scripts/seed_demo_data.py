import argparse
import os

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import hash_password
from app.db.user import User
from app.onboarding.personas import PERSONAS
from app.onboarding.service import seed_persona


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic Financial Health Copilot personas")
    parser.add_argument("--persona", choices=["all", *PERSONAS], default="all")
    args = parser.parse_args()
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit("Demo seeding is disabled in production.")
    password = os.environ.get("DEMO_USER_PASSWORD", "demo-passphrase-2026")
    keys = list(PERSONAS) if args.persona == "all" else [args.persona]
    with get_session_factory()() as db:
        for key in keys:
            email = f"{key}.demo@example.com"
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    name=PERSONAS[key]["display_name"],
                    password_hash=hash_password(password),
                )
                db.add(user)
                db.flush()
            result = seed_persona(db, user.id, key)
            print(
                f"{key}: {result['transactions_ingested']} imported, "
                f"{result['duplicates_skipped']} duplicates skipped ({email})"
            )
        db.commit()


if __name__ == "__main__":
    main()
