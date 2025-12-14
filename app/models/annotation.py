from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    annotator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    annotation_data = Column(JSONB, nullable=False)
    label_studio_annotation_id = Column(Integer)
    time_spent = Column(Integer)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    task = relationship("Task", back_populates="annotations")
    reviews = relationship("Review", back_populates="annotation", cascade="all, delete-orphan")