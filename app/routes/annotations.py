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
from app.services.annotation_service import AnnotationService
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
    
    try:
        service = AnnotationService(db)
        return service.create_annotation(annotation_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create annotation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create annotation")

@router.get("/ls-result/{ls_task_id}")
def get_ls_annotation_result(
    ls_task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch annotation result from Label Studio for a task"""
    try:
        ls_service = LabelStudioService()
        ls_task = ls_service.get_task(ls_task_id)

        annotations = ls_task.get("annotations", [])
        if annotations:
            latest = annotations[-1]
            return {
                "result": {
                    "result": latest.get("result", []),
                    "label_studio_annotation_id": latest.get("id")
                }
            }
        return {"result": {"result": [], "note": "No annotation found in Label Studio"}}
    except Exception as e:
        logger.error(f"Failed to fetch LS annotation: {e}")
        return {"result": {"result": [], "note": "Submitted via Label Studio"}}

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