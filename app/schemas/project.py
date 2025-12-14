from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    label_config: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    label_config: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(ProjectBase):
    id: UUID4
    label_studio_project_id: Optional[int] = None
    created_by: Optional[UUID4] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProjectWithStats(ProjectResponse):
    total_tasks: int = 0
    completed_tasks: int = 0
    pending_tasks: int = 0
