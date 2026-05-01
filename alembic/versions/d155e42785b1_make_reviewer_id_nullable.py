"""make reviewer_id nullable

Revision ID: d155e42785b1
Revises: 72e8ddb3517e
Create Date: 2026-05-01 20:47:49.078703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd155e42785b1'
down_revision: Union[str, Sequence[str], None] = '72e8ddb3517e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('annotations', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('annotations', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_index(op.f('idx_annotations_task_id'), table_name='annotations')
    op.alter_column('assets', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('export_jobs', 'export_format',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.Enum('JSON', 'JSONL', 'COCO', 'YOLO', 'CSV', name='exportformat'),
               existing_nullable=False,
               postgresql_using="export_format::text::exportformat")
    op.execute("ALTER TABLE export_jobs ALTER COLUMN status DROP DEFAULT")
    op.alter_column('export_jobs', 'status',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='exportstatus'),
               existing_nullable=True,
               postgresql_using="status::text::exportstatus")
    op.execute("ALTER TABLE export_jobs ALTER COLUMN status SET DEFAULT 'PENDING'")
    op.alter_column('export_jobs', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('export_jobs', 'completed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('projects', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('projects', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('reviews', 'annotation_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.execute("ALTER TABLE reviews ALTER COLUMN status DROP DEFAULT")
    op.alter_column('reviews', 'status',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='reviewstatus'),
               existing_nullable=True,
               postgresql_using="status::text::reviewstatus")
    op.execute("ALTER TABLE reviews ALTER COLUMN status SET DEFAULT 'PENDING'")
    op.alter_column('reviews', 'reviewed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('reviews', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_index(op.f('idx_reviews_status'), table_name='reviews')
    op.execute("ALTER TABLE tasks ALTER COLUMN status DROP DEFAULT")
    op.alter_column('tasks', 'status',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.Enum('UNASSIGNED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'REVIEWED', name='taskstatus'),
               existing_nullable=True,
               postgresql_using="status::text::taskstatus")
    op.execute("ALTER TABLE tasks ALTER COLUMN status SET DEFAULT 'UNASSIGNED'")
    op.alter_column('tasks', 'assigned_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('tasks', 'started_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('tasks', 'completed_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('tasks', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('tasks', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_index(op.f('idx_tasks_assigned_to'), table_name='tasks')
    op.drop_index(op.f('idx_tasks_project_id'), table_name='tasks')
    op.drop_index(op.f('idx_tasks_status'), table_name='tasks')
    op.create_index('ix_task_assigned_status', 'tasks', ['assigned_to', 'status'], unique=False)
    op.create_index('ix_task_priority', 'tasks', ['priority'], unique=False)
    op.create_index('ix_task_project_status', 'tasks', ['project_id', 'status'], unique=False)
    op.alter_column('users', 'avatar_url',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    
    # Drop ALL policies that depend on the role column from all tables
    op.execute("DROP POLICY IF EXISTS \"admin read users\" ON users")
    op.execute("DROP POLICY IF EXISTS \"admin full access projects\" ON projects")
    op.execute("DROP POLICY IF EXISTS \"admin manage tasks\" ON tasks")
    op.execute("DROP POLICY IF EXISTS \"admin export jobs\" ON export_jobs")
    
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.Enum('ADMIN', 'ANNOTATOR', 'REVIEWER', name='userrole'),
               existing_nullable=True,
               postgresql_using="role::text::userrole")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'ANNOTATOR'")
    
    # Recreate all policies with exact original definitions
    op.execute("""
        CREATE POLICY "admin read users" ON users
        FOR SELECT
        USING (EXISTS (SELECT 1 FROM users u WHERE (u.id = auth.uid()) AND ((u.role)::text = 'admin'::text)))
    """)
    
    op.execute("""
        CREATE POLICY "admin full access projects" ON projects
        FOR ALL
        USING (EXISTS (SELECT 1 FROM users WHERE (users.id = auth.uid()) AND ((users.role)::text = 'admin'::text)))
    """)
    
    op.execute("""
        CREATE POLICY "admin manage tasks" ON tasks
        FOR ALL
        USING (EXISTS (SELECT 1 FROM users WHERE (users.id = auth.uid()) AND ((users.role)::text = 'admin'::text)))
    """)
    
    op.execute("""
        CREATE POLICY "admin export jobs" ON export_jobs
        FOR ALL
        USING (EXISTS (SELECT 1 FROM users WHERE (users.id = auth.uid()) AND ((users.role)::text = 'admin'::text)))
    """)
    
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_constraint(op.f('users_email_key'), 'users', type_='unique')
    op.drop_constraint(op.f('users_provider_provider_id_key'), 'users', type_='unique')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_unique_constraint(op.f('users_provider_provider_id_key'), 'users', ['provider', 'provider_id'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('users_email_key'), 'users', ['email'], postgresql_nulls_not_distinct=False)
    op.alter_column('users', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    
    # Drop policies before altering column back
    op.execute("DROP POLICY IF EXISTS \"admin read users\" ON users")
    op.execute("DROP POLICY IF EXISTS \"admin full access projects\" ON projects")
    op.execute("DROP POLICY IF EXISTS \"admin manage tasks\" ON tasks")
    op.execute("DROP POLICY IF EXISTS \"admin export jobs\" ON export_jobs")
    
    op.alter_column('users', 'role',
               existing_type=sa.Enum('ADMIN', 'ANNOTATOR', 'REVIEWER', name='userrole'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True,
               existing_server_default=sa.text("'ANNOTATOR'::character varying"))
    
    # Recreate policies with exact original definitions
    op.execute("""
        CREATE POLICY "admin read users" ON users
        FOR SELECT
        USING (EXISTS (SELECT 1 FROM users u WHERE (u.id = auth.uid()) AND ((u.role)::text = 'admin'::text)))
    """)
    
    op.execute("""
        CREATE POLICY "admin full access projects" ON projects
        FOR ALL
        USING (EXISTS (SELECT 1 FROM users WHERE (users.id = auth.uid()) AND ((users.role)::text = 'admin'::text)))
    """)
    
    op.execute("""
        CREATE POLICY "admin manage tasks" ON tasks
        FOR ALL
        USING (EXISTS (SELECT 1 FROM users WHERE (users.id = auth.uid()) AND ((users.role)::text = 'admin'::text)))
    """)
    
    op.execute("""
        CREATE POLICY "admin export jobs" ON export_jobs
        FOR ALL
        USING (EXISTS (SELECT 1 FROM users WHERE (users.id = auth.uid()) AND ((users.role)::text = 'admin'::text)))
    """)
    
    op.alter_column('users', 'avatar_url',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.drop_index('ix_task_project_status', table_name='tasks')
    op.drop_index('ix_task_priority', table_name='tasks')
    op.drop_index('ix_task_assigned_status', table_name='tasks')
    op.create_index(op.f('idx_tasks_status'), 'tasks', ['status'], unique=False)
    op.create_index(op.f('idx_tasks_project_id'), 'tasks', ['project_id'], unique=False)
    op.create_index(op.f('idx_tasks_assigned_to'), 'tasks', ['assigned_to'], unique=False)
    op.alter_column('tasks', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('tasks', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('tasks', 'completed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('tasks', 'started_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('tasks', 'assigned_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('tasks', 'status',
               existing_type=sa.Enum('UNASSIGNED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'REVIEWED', name='taskstatus'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True,
               existing_server_default=sa.text("'UNASSIGNED'::character varying"))
    op.create_index(op.f('idx_reviews_status'), 'reviews', ['status'], unique=False)
    op.alter_column('reviews', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('reviews', 'reviewed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('reviews', 'status',
               existing_type=sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='reviewstatus'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True,
               existing_server_default=sa.text("'PENDING'::character varying"))
    op.alter_column('reviews', 'annotation_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.alter_column('projects', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('projects', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('export_jobs', 'completed_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('export_jobs', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('export_jobs', 'status',
               existing_type=sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='exportstatus'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True,
               existing_server_default=sa.text("'PENDING'::character varying"))
    op.alter_column('export_jobs', 'export_format',
               existing_type=sa.Enum('JSON', 'JSONL', 'COCO', 'YOLO', 'CSV', name='exportformat'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)
    op.alter_column('assets', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.create_index(op.f('idx_annotations_task_id'), 'annotations', ['task_id'], unique=False)
    op.alter_column('annotations', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('annotations', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))