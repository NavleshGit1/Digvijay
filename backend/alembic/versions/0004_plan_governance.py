"""plan governance, approval records and constraint sets v1

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20 02:00:00.000000

"""
import json
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Add governance fields to plan_versions if not present
    pv_cols = {c['name'] for c in insp.get_columns('plan_versions')}
    
    if 'stale_reason' not in pv_cols:
        op.add_column('plan_versions', sa.Column('stale_reason', sa.String(length=255), nullable=True))
    if 'refreshed_from' not in pv_cols:
        op.add_column('plan_versions', sa.Column('refreshed_from', sa.Integer(), nullable=True))
    if 'rollback_target' not in pv_cols:
        op.add_column('plan_versions', sa.Column('rollback_target', sa.Integer(), nullable=True))
    if 'proposal_group_id' not in pv_cols:
        op.add_column('plan_versions', sa.Column('proposal_group_id', sa.String(length=100), nullable=True))
    if 'rejection_reason' not in pv_cols:
        op.add_column('plan_versions', sa.Column('rejection_reason', sa.String(length=255), nullable=True))
    if 'created_by' not in pv_cols:
        op.add_column('plan_versions', sa.Column('created_by', sa.String(length=100), nullable=True))

    # 2. Create approval_records table if not present
    if 'approval_records' not in existing_tables:
        op.create_table(
            'approval_records',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id', ondelete='CASCADE'), nullable=False),
            sa.Column('plan_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_versions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('decision', sa.String(length=50), nullable=False),
            sa.Column('reason', sa.String(length=1000), nullable=False),
            sa.Column('idempotency_key', sa.String(length=100), nullable=True, index=True),
            sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )

    # 3. Create constraint_sets table if not present
    if 'constraint_sets' not in existing_tables:
        op.create_table(
            'constraint_sets',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('version', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
            sa.Column('parameters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )

    # 4. Insert default active constraint set v1.0
    c_set_id = str(uuid.uuid4())
    params = json.dumps({
        "min_turnaround_minutes": 45,
        "max_flight_hours_daily": 8,
        "max_crew_duty_hours": 12,
        "min_crew_rest_hours": 10,
        "enforce_qualification": True,
        "enforce_asset_maintenance": True,
        "enforce_task_dependencies": True,
        "enforce_temporal_windows": True,
    })
    op.execute(
        f"""
        INSERT INTO constraint_sets (id, version, name, status, parameters_json, created_by, is_synthetic, created_at, updated_at)
        VALUES ('{c_set_id}', 'v1.0', 'Standard Operational Constraints v1', 'active', '{params}'::jsonb, 'system', true, now(), now())
        ON CONFLICT (version) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_column('plan_versions', 'created_by')
    op.drop_column('plan_versions', 'rejection_reason')
    op.drop_column('plan_versions', 'proposal_group_id')
    op.drop_column('plan_versions', 'rollback_target')
    op.drop_column('plan_versions', 'refreshed_from')
    op.drop_column('plan_versions', 'stale_reason')
