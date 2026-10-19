"""data foundation schema v1

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Zones
    op.create_table(
        'zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('code', sa.String(length=20), nullable=False, unique=True),
        sa.Column('capacity_limit', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('coordinates_geojson', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_zones_code', 'zones', ['code'])

    # 2. Assets
    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('identifier', sa.String(length=50), nullable=False, unique=True),
        sa.Column('asset_type', sa.String(length=50), nullable=False, server_default='FIGHTER_MULTIROLE'),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='available'),
        sa.Column('health_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('current_location', sa.String(length=100), nullable=True),
        sa.Column('flight_hours', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cycles', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_assets_identifier', 'assets', ['identifier'])
    op.create_index('ix_assets_asset_type', 'assets', ['asset_type'])
    op.create_index('ix_assets_status', 'assets', ['status'])

    # 3. Personnel
    op.create_table(
        'personnel',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('callsign', sa.String(length=50), nullable=True),
        sa.Column('role_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='available'),
        sa.Column('duty_hours_accumulated', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('home_zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_personnel_role_type', 'personnel', ['role_type'])
    op.create_index('ix_personnel_status', 'personnel', ['status'])

    # 4. Qualifications
    op.create_table(
        'qualifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('validity_days', sa.Integer(), nullable=False, server_default='365'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_qualifications_code', 'qualifications', ['code'])

    # 5. Personnel Qualifications Join Table
    op.create_table(
        'personnel_qualifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('personnel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personnel.id'), nullable=False),
        sa.Column('qualification_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('qualifications.id'), nullable=False),
        sa.Column('acquired_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 6. Resource Inventory
    op.create_table(
        'resource_inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('item_code', sa.String(length=50), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('quantity_on_hand', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reorder_threshold', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_resource_inventory_item_code', 'resource_inventory', ['item_code'])

    # 7. Parts Catalog
    op.create_table(
        'parts_catalog',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('part_number', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('unit_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_parts_catalog_part_number', 'parts_catalog', ['part_number'])
    op.create_index('ix_parts_catalog_category', 'parts_catalog', ['category'])

    # 8. Spares Inventory
    op.create_table(
        'spares_inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('part_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('parts_catalog.id'), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('on_hand', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reserved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('minimum_safety_level', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Maintenance Rules
    op.create_table(
        'maintenance_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('trigger_type', sa.String(length=50), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('tolerance', sa.Float(), nullable=False, server_default='0.05'),
        sa.Column('estimated_duration_hours', sa.Float(), nullable=False, server_default='4.0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_maintenance_rules_code', 'maintenance_rules', ['code'])

    # 10. Maintenance Part Requirements
    op.create_table(
        'maintenance_part_requirements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('maintenance_rules.id'), nullable=False),
        sa.Column('part_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('parts_catalog.id'), nullable=False),
        sa.Column('quantity_required', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 11. Resupply Orders
    op.create_table(
        'resupply_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('part_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('parts_catalog.id'), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('ordered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('estimated_arrival', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_transit'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 12. Tasks
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('earliest_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('latest_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='routine'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_tasks_code', 'tasks', ['code'])
    op.create_index('ix_tasks_category', 'tasks', ['category'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])

    # 13. Task Requirements
    op.create_table(
        'task_requirements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('asset_type_required', sa.String(length=50), nullable=False),
        sa.Column('crew_headcount', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('required_qualification_code', sa.String(length=50), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 14. Task Dependencies
    op.create_table(
        'task_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('predecessor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('successor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('min_lag_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 15. Task Executions
    op.create_table(
        'task_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('plan_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actual_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delay_minutes', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_disrupted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 16. Maintenance Records
    op.create_table(
        'maintenance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id'), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('predicted_completion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_unplanned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='scheduled'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 17. Data Sources
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('adapter_type', sa.String(length=50), nullable=False),
        sa.Column('expected_interval_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 18. Ingestion Runs
    op.create_table(
        'ingestion_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id'), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 19. Source Records
    op.create_table(
        'source_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id'), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 20. Dataset Versions
    op.create_table(
        'dataset_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version_tag', sa.String(length=50), nullable=False, unique=True),
        sa.Column('generator_version', sa.String(length=50), nullable=False, server_default='1.1'),
        sa.Column('seed', sa.Integer(), nullable=False),
        sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('entity_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_dataset_versions_version_tag', 'dataset_versions', ['version_tag'])

    # 21. Data Source Freshness
    op.create_table(
        'data_source_freshness',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id'), nullable=False, unique=True),
        sa.Column('last_successful_sync', sa.DateTime(timezone=True), nullable=False),
        sa.Column('staleness_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_stale', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 22. Data Quality Issues
    op.create_table(
        'data_quality_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_sources.id'), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('issue_class', sa.String(length=50), nullable=False, server_default='integrity_error'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('raw_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('expected_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_data_quality_issues_entity_type', 'data_quality_issues', ['entity_type'])

    # 23. Events
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False, unique=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='synthetic_generator'),
        sa.Column('affected_entity_type', sa.String(length=50), nullable=False),
        sa.Column('affected_entity_id', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_events_idempotency_key', 'events', ['idempotency_key'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])

    # 24. Plans
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('current_approved_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 25. Plan Versions
    op.create_table(
        'plan_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=50), nullable=False, server_default='baseline'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='proposed'),
        sa.Column('based_on_version', sa.Integer(), nullable=True),
        sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
        sa.Column('solver_status', sa.String(length=50), nullable=False, server_default='optimal'),
        sa.Column('plan_source', sa.String(length=50), nullable=False, server_default='cpsat'),
        sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 26. Plan Assignments
    op.create_table(
        'plan_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plan_versions.id'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id'), nullable=True),
        sa.Column('personnel_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('assigned_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('plan_assignments')
    op.drop_table('plan_versions')
    op.drop_table('plans')
    op.drop_table('events')
    op.drop_table('data_quality_issues')
    op.drop_table('data_source_freshness')
    op.drop_table('dataset_versions')
    op.drop_table('source_records')
    op.drop_table('ingestion_runs')
    op.drop_table('data_sources')
    op.drop_table('maintenance_records')
    op.drop_table('task_executions')
    op.drop_table('task_dependencies')
    op.drop_table('task_requirements')
    op.drop_table('tasks')
    op.drop_table('resupply_orders')
    op.drop_table('maintenance_part_requirements')
    op.drop_table('maintenance_rules')
    op.drop_table('spares_inventory')
    op.drop_table('parts_catalog')
    op.drop_table('resource_inventory')
    op.drop_table('personnel_qualifications')
    op.drop_table('qualifications')
    op.drop_table('personnel')
    op.drop_table('assets')
    op.drop_table('zones')
