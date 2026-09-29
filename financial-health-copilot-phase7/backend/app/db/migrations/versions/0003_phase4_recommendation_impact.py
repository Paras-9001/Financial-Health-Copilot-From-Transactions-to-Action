"""Add the persisted expected impact required by Phase 4 recommendations."""

from alembic import op

revision = "0003_phase4"
down_revision = "0002_phase1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE recommendations ADD COLUMN expected_impact JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE recommendations ALTER COLUMN expected_impact DROP DEFAULT")


def downgrade():
    op.execute("ALTER TABLE recommendations DROP COLUMN expected_impact")
