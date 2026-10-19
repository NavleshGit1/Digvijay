"""scheduling and optimisation schema v1

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20 01:00:00.000000

"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add fields to plan_versions
    op.add_column('plan_versions', sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('plan_versions', sa.Column('solver_runtime_seconds', sa.Float(), nullable=True))
    op.add_column('plan_versions', sa.Column('run_manifest_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('plan_versions', sa.Column('constraint_set_version', sa.String(length=50), nullable=True))
    op.add_column('plan_versions', sa.Column('weight_set_version', sa.Integer(), nullable=True))

    # 2. Add is_locked to plan_assignments
    op.add_column('plan_assignments', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'))

    # 3. Create plan_validations table
    op.create_table(
        'plan_validations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_versions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('violation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('violations_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('binding_constraints_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 4. Create objective_weight_sets table
    op.create_table(
        'objective_weight_sets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.Integer(), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False, server_default='Standard Operational Weights v1'),
        sa.Column('delay_weight', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('completion_weight', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('churn_weight', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('balance_weight', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('buffer_weight', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 5. Insert default objective_weight_sets (version=1)
    weight_set_id = str(uuid.uuid4())
    op.execute(
        f"""
        INSERT INTO objective_weight_sets (id, version, name, delay_weight, completion_weight, churn_weight, balance_weight, buffer_weight, is_active, is_synthetic, created_at, updated_at)
        VALUES ('{weight_set_id}', 1, 'Standard Operational Weights v1', 10, 1000, 50, 5, 20, true, true, now(), now())
        ON CONFLICT (version) DO NOTHING;
        """
    )

    # 6. Create approved_assignments SQL view
    op.execute(
        """
        CREATE OR REPLACE VIEW approved_assignments AS
        SELECT pa.*
        FROM plan_assignments pa
        JOIN plan_versions pv ON pa.plan_version_id = pv.id
        JOIN plans p ON pv.plan_id = p.id
        WHERE p.current_approved_version_id = pv.id;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS approved_assignments;")
    op.drop_table('objective_weight_sets')
    op.drop_table('plan_validations')
    op.drop_column('plan_assignments', 'is_locked')
    op.drop_column('plan_versions', 'weight_set_version')
    op.drop_column('plan_versions', 'constraint_set_version')
    op.drop_column('plan_versions', 'run_manifest_json')
    op.drop_column('plan_versions', 'solver_runtime_seconds')
    op.drop_column('plan_versions', 'metrics_json')
