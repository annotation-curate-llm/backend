from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional
from app.models.task import TaskStatus

class TaskBase(BaseModel):
    priority: int = 0

class TaskCreate(TaskBase):
    asset_id: UUID4
    project_id: UUID4

class TaskUpdate(BaseModel):
    assigned_to: Optional[UUID4] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = None

class TaskResponse(BaseModel):
    id: UUID4
    asset_id: UUID4
    project_id: UUID4
    assigned_to: Optional[UUID4] = None
    status: TaskStatus
    label_studio_task_id: Optional[int] = None
    priority: int
    created_at: datetime
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskWithAsset(TaskResponse):
    file_url: str
    file_name: str
    mime_type: Optional[str] = None