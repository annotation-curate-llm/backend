from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.models.asset import Asset
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate, TaskWithAsset

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Create new task (admin only)"""
    new_task = Task(**task_data.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.get("/my-tasks", response_model=List[TaskWithAsset])
def get_my_tasks(
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tasks assigned to current user"""
    query = db.query(Task).join(Asset).filter(Task.assigned_to == current_user.id)
    
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.all()
    
    result = []
    for task in tasks:
        task_dict = TaskWithAsset.model_validate(task).model_dump()
        task_dict["file_url"] = task.asset.file_url
        task_dict["file_name"] = task.asset.file_name
        task_dict["mime_type"] = task.asset.mime_type
        result.append(TaskWithAsset(**task_dict))
    
    return result

@router.get("/next", response_model=TaskWithAsset)
def get_next_task(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get next available task for annotator"""
    task = db.query(Task).join(Asset).filter(
        Task.assigned_to == current_user.id,
        Task.status == TaskStatus.ASSIGNED
    ).order_by(Task.priority.desc(), Task.created_at).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="No tasks available")
    
    task_dict = TaskWithAsset.model_validate(task).model_dump()
    task_dict["file_url"] = task.asset.file_url
    task_dict["file_name"] = task.asset.file_name
    task_dict["mime_type"] = task.asset.mime_type
    
    return TaskWithAsset(**task_dict)

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    
    if task_update.status == TaskStatus.IN_PROGRESS and not task.started_at:
        task.started_at = datetime.utcnow()
    
    if task_update.status == TaskStatus.COMPLETED and not task.completed_at:
        task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    return task

@router.post("/assign", status_code=status.HTTP_200_OK)
def assign_tasks(
    project_id: UUID,
    user_id: UUID,
    count: int = 10,
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Assign tasks to a user (admin only)"""
    tasks = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == TaskStatus.UNASSIGNED
    ).limit(count).all()
    
    for task in tasks:
        task.assigned_to = user_id
        task.status = TaskStatus.ASSIGNED
        task.assigned_at = datetime.utcnow()
    
    db.commit()
    return {"assigned_count": len(tasks)}