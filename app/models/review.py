from sqlalchemy import Column, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base

class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    annotation_id = Column(UUID(as_uuid=True), ForeignKey("annotations.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING)
    comments = Column(Text)
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    annotation = relationship("Annotation", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")