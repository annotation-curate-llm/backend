from alembic import op
import sqlalchemy as sa

revision = '72e8ddb3517e'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('tasks', sa.Column('label_studio_project_id', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('tasks', 'label_studio_project_id')