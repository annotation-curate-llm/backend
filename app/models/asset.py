from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime
import uuid
from app.core.database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_url = Column(Text, nullable=False)
    mime_type = Column(String(100))
    file_size = Column(Integer)
    text_content = Column(Text, nullable=True)
    asset_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="assets")
    tasks = relationship("Task", back_populates="asset", cascade="all, delete-orphan")