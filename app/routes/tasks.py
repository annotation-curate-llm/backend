from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.task import TaskStatus
from app.schemas.task import (
    TaskCreate, 
    TaskResponse, 
    TaskUpdate, 
    TaskWithAsset,
    TaskAssignRequest,
    TaskAssignResponse,
    AssetInfo
)
from app.services.task_service import TaskService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    label_studio_project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Create new task (admin only)"""
    try:
        task_service = TaskService(db)
        new_task = task_service.create_task(task_data, label_studio_project_id)
        return new_task
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/my-tasks", response_model=List[TaskWithAsset])
def get_my_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tasks assigned to current user with pagination"""
    task_service = TaskService(db)
    tasks = task_service.get_user_tasks(
        user_id=current_user.id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    
    result = []
    for task in tasks:
        if not task.asset:
            logger.warning(f"Task {task.id} has no associated asset")
            continue
        
        result.append(
            TaskWithAsset(
                id=task.id,
                asset_id=task.asset_id,
                project_id=task.project_id,
                assigned_to=task.assigned_to,
                status=task.status,
                label_studio_task_id=task.label_studio_task_id,
                label_studio_project_id=task.project.label_studio_project_id if task.project else None,  # ADD THIS
                priority=task.priority,
                created_at=task.created_at,
                updated_at=task.updated_at,
                assigned_at=task.assigned_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                asset=AssetInfo(
                    file_url=task.asset.file_url,
                    file_name=task.asset.file_name,
                    mime_type=task.asset.mime_type
                )
            )
        )
    
    return result


@router.get("/next", response_model=TaskWithAsset)
def get_next_task(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get next available task for annotator"""
    task_service = TaskService(db)
    task = task_service.get_next_task(current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tasks available"
        )
    
    if not task.asset:
        logger.error(f"Task {task.id} has no associated asset")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task data is incomplete"
        )
    
    return TaskWithAsset(
        id=task.id,
        asset_id=task.asset_id,
        project_id=task.project_id,
            assigned_to=task.assigned_to,
        status=task.status,
        label_studio_task_id=task.label_studio_task_id,
        priority=task.priority,
        created_at=task.created_at,
        updated_at=task.updated_at,
        assigned_at=task.assigned_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        asset=AssetInfo(
            file_url=task.asset.file_url,
            file_name=task.asset.file_name,
            mime_type=task.asset.mime_type
        )
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific task by ID"""
    task_service = TaskService(db)
    task = task_service.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify access
    if not task_service.verify_task_access(task_id, current_user.id, current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task"
        )
    
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update task"""
    task_service = TaskService(db)
    
    # Verify task exists and user has access
    if not task_service.verify_task_access(task_id, current_user.id, current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )
    
    try:
        updated_task = task_service.update_task(task_id, task_update)
        
        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return updated_task
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.post("/assign", response_model=TaskAssignResponse)
def assign_tasks(
    assign_request: TaskAssignRequest,
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Assign tasks to a user (admin only)"""
    try:
        task_service = TaskService(db)
        assigned_count = task_service.assign_tasks(
            project_id=assign_request.project_id,
            user_id=assign_request.user_id,
            count=assign_request.count
        )
        
        return TaskAssignResponse(
            assigned_count=assigned_count,
            message=f"Successfully assigned {assigned_count} tasks"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to assign tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign tasks"
        )


@router.post("/auto-assign", response_model=dict)
def auto_assign_tasks(
    project_id: UUID,
    tasks_per_user: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Auto-assign tasks to available annotators (admin only)"""
    try:
        task_service = TaskService(db)
        assignment_map = task_service.auto_assign_tasks(
            project_id=project_id,
            tasks_per_user=tasks_per_user
        )
        
        total_assigned = sum(assignment_map.values())
        
        return {
            "total_assigned": total_assigned,
            "assignments": assignment_map,
            "message": f"Successfully assigned {total_assigned} tasks to {len(assignment_map)} annotators"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to auto-assign tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to auto-assign tasks"
        )


@router.get("/project/{project_id}", response_model=List[TaskResponse])
def get_project_tasks(
    project_id: UUID,
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Get all tasks for a project (admin only)"""
    task_service = TaskService(db)
    tasks = task_service.get_project_tasks(
        project_id=project_id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    return tasks


@router.post("/bulk-update-status", response_model=dict)
def bulk_update_status(
    task_ids: List[UUID],
    new_status: TaskStatus,
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Bulk update task status (admin only)"""
    if not task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No task IDs provided"
        )
    
    try:
        task_service = TaskService(db)
        updated_count = task_service.bulk_update_status(task_ids, new_status)
        
        return {
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} tasks to {new_status.value}"
        }
        
    except Exception as e:
        logger.error(f"Failed to bulk update tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk update tasks"
        )