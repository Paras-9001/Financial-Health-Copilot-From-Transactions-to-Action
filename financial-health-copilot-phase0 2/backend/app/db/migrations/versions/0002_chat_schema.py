"""Add Phase 5 chat response persistence fields."""

from alembic import op

revision = "0002_chat_schema"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(160)")
    op.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS structured_answer JSONB")


def downgrade():
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS structured_answer")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS title")
