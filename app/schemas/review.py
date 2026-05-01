from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional
from app.models.review import ReviewStatus

class ReviewBase(BaseModel):
    status: ReviewStatus
    comments: Optional[str] = None

class ReviewCreate(BaseModel):
    annotation_id: UUID4
    status: ReviewStatus
    comments: Optional[str] = None

class ReviewUpdate(BaseModel):
    status: Optional[ReviewStatus] = None
    comments: Optional[str] = None

class ReviewResponse(ReviewBase):
    id: UUID4
    annotation_id: UUID4
    reviewer_id: Optional[UUID4] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ReviewWithAnnotation(ReviewResponse):
    task_id: UUID4
    annotator_id: Optional[UUID4] = None
    annotation_data: Optional[dict] = None
    file_url: str
    file_name: str