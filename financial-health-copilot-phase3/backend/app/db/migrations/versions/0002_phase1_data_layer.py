"""Add per-user merchant category memory for Phase 1."""

from alembic import op

revision = "0002_phase1"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE merchant_category_overrides (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
            category_id UUID NOT NULL REFERENCES categories(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(user_id, merchant_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_merchant_override_user ON merchant_category_overrides(user_id)")


def downgrade():
    op.execute("DROP TABLE merchant_category_overrides")
