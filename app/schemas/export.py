from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional
from app.models.export_job import ExportFormat, ExportStatus

class ExportJobBase(BaseModel):
    export_format: ExportFormat

class ExportJobCreate(ExportJobBase):
    project_id: UUID4

class ExportJobResponse(BaseModel):
    id: UUID4
    project_id: UUID4
    created_by: Optional[UUID4] = None
    export_format: ExportFormat
    status: ExportStatus
    file_url: Optional[str] = None
    total_annotations: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ExportJobWithProgress(ExportJobResponse):
    progress_percentage: Optional[float] = None
    estimated_time_remaining: Optional[int] = None  # seconds