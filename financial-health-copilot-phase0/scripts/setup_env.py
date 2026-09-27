"""Generate local-only credentials without overwriting an existing .env."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
destination = root / ".env"
if destination.exists():
    raise SystemExit(".env already exists; it was not modified.")
content = (root / ".env.example").read_text()
for label in ("admin", "owner", "app", "jwt"):
    content = content.replace(f"replace-with-generated-{label}-secret", secrets.token_hex(32))
with destination.open("x") as f:
    f.write(content)
destination.chmod(0o600)
print("Created .env. Keep it private; do not commit it.")
