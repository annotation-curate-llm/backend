from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional
from app.models.task import TaskStatus

class TaskBase(BaseModel):
    priority: int = Field(default=0, ge=0, le=100)

class TaskCreate(TaskBase):
    asset_id: UUID4
    project_id: UUID4

class TaskUpdate(BaseModel):
    assigned_to: Optional[UUID4] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = Field(None, ge=0, le=100)

class TaskResponse(BaseModel):
    id: UUID4
    asset_id: UUID4
    project_id: UUID4
    assigned_to: Optional[UUID4] = None
    status: TaskStatus
    label_studio_task_id: Optional[int] = None
    priority: int
    created_at: datetime
    updated_at: datetime
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AssetInfo(BaseModel):
    file_url: str
    file_name: str
    mime_type: Optional[str] = None

class TaskWithAsset(TaskResponse):
    asset: AssetInfo
    
    class Config:
        from_attributes = True

class TaskAssignRequest(BaseModel):
    project_id: UUID4
    user_id: UUID4
    count: int = Field(default=10, ge=1, le=100)

class TaskAssignResponse(BaseModel):
    assigned_count: int
    message: str