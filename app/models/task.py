from sqlalchemy import Column, DateTime, Integer, ForeignKey, Enum as SQLEnum, Index, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from app.core.database import Base

class TaskStatus(str, enum.Enum):
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.UNASSIGNED)
    label_studio_task_id = Column(Integer, nullable=True)
    label_studio_project_id = Column(Integer, nullable=True)
    priority = Column(Integer, default=0)
    assigned_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("Asset", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    annotations = relationship("Annotation", back_populates="task", cascade="all, delete-orphan")
    
    # Add indices for frequent queries
    __table_args__ = (
        Index('ix_task_assigned_status', 'assigned_to', 'status'),
        Index('ix_task_project_status', 'project_id', 'status'),
        Index('ix_task_priority', 'priority'),
    )

# Auto-update updated_at timestamp
@event.listens_for(Task, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()