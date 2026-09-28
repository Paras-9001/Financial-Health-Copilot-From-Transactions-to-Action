"""Add Phase 5 structured chat persistence."""

from alembic import op

revision = "0004_phase5"
down_revision = "0003_phase4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(160)")
    op.execute("ALTER TABLE chat_messages ADD COLUMN structured_answer JSONB")


def downgrade():
    op.execute("ALTER TABLE chat_messages DROP COLUMN structured_answer")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN title")
