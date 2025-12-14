from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, Dict, Any

class AnnotationBase(BaseModel):
    annotation_data: Dict[Any, Any]
    time_spent: Optional[int] = None

class AnnotationCreate(AnnotationBase):
    task_id: UUID4

class AnnotationUpdate(BaseModel):
    annotation_data: Optional[Dict[Any, Any]] = None
    time_spent: Optional[int] = None

class AnnotationResponse(AnnotationBase):
    id: UUID4
    task_id: UUID4
    annotator_id: Optional[UUID4] = None
    label_studio_annotation_id: Optional[int] = None
    version: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True