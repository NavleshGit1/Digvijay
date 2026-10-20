"""events, replanning and alert subsystem v1

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-20 08:45:00.000000

"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Create alert_rules table
    if 'alert_rules' not in existing_tables:
        op.create_table(
            'alert_rules',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('rule_code', sa.String(length=50), nullable=False, unique=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),
            sa.Column('description', sa.Text(), nullable=False, server_default=''),
            sa.Column('threshold_value', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('hysteresis_buffer', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('scope', sa.String(length=50), nullable=False, server_default='global'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_alert_rules_rule_code', 'alert_rules', ['rule_code'])

    # 2. Create alerts table
    if 'alerts' not in existing_tables:
        op.create_table(
            'alerts',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('rule_code', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='new'),
            sa.Column('dedup_key', sa.String(length=100), nullable=False),
            sa.Column('entity_type', sa.String(length=50), nullable=False),
            sa.Column('entity_id', sa.String(length=100), nullable=False),
            sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
            sa.Column('count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolved_by', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_alerts_rule_code', 'alerts', ['rule_code'])
        op.create_index('ix_alerts_severity', 'alerts', ['severity'])
        op.create_index('ix_alerts_status', 'alerts', ['status'])
        op.create_index('ix_alerts_dedup_key', 'alerts', ['dedup_key'])
        op.create_index('ix_alerts_entity_type', 'alerts', ['entity_type'])
        op.create_index('ix_alerts_entity_id', 'alerts', ['entity_id'])


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('alert_rules')
