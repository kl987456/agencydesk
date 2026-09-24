"""initial AgencyDesk schema with tenant-safe keys and Postgres RLS"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        for table in ["clients", "projects", "project_assignments", "tasks", "comments", "time_entries", "file_attachments", "invites", "leads", "deals", "contracts", "intake_forms", "intake_responses", "automations", "notifications"]:
            op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
            op.execute(sa.text(f"CREATE POLICY {table}_tenant_isolation ON {table} USING (agency_id::text = current_setting('app.current_agency_id', true)) WITH CHECK (agency_id::text = current_setting('app.current_agency_id', true))"))

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
