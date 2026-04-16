from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.annotation import Annotation
from app.models.task import Task, TaskStatus
from app.schemas.annotation import AnnotationCreate, AnnotationResponse
from app.services.label_studio_service import LabelStudioService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/annotations", tags=["Annotations"])

@router.post("/", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
def create_annotation(
    annotation_data: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create annotation for a task and sync to Label Studio"""
    task = db.query(Task).filter(Task.id == annotation_data.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Task not assigned to you")
    
    # Save to your DB
    new_annotation = Annotation(
        **annotation_data.model_dump(),
        annotator_id=current_user.id
    )
    db.add(new_annotation)
    task.status = TaskStatus.COMPLETED
    db.commit()
    db.refresh(new_annotation)
    
    # Sync to Label Studio (non-blocking — don't fail if LS is down)
    if task.label_studio_task_id:
        try:
            ls_service = LabelStudioService()
            ls_service.create_annotation(
                task_id=task.label_studio_task_id,
                result=annotation_data.annotation_data.get("result", [])
            )
        except Exception as e:
            # Log but don't fail — DB is source of truth
            logger.error(f"Failed to sync annotation to Label Studio (task {task.id}): {e}")
    else:
        logger.warning(f"Task {task.id} has no label_studio_task_id — skipping LS sync")
    
    return new_annotation

@router.get("/task/{task_id}", response_model=List[AnnotationResponse])
def get_task_annotations(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all annotations for a task"""
    annotations = db.query(Annotation).filter(Annotation.task_id == task_id).all()
    return annotations

@router.get("/{annotation_id}", response_model=AnnotationResponse)
def get_annotation(
    annotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get annotation by ID"""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return annotation