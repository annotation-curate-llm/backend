from sqlalchemy.orm import Session
from app.models.annotation import Annotation
from app.models.task import Task, TaskStatus
from app.models.review import Review, ReviewStatus
from app.schemas.annotation import AnnotationCreate, AnnotationUpdate
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnnotationService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_annotation(
        self, 
        annotation_data: AnnotationCreate,
        annotator_id: UUID
    ) -> Annotation:
        """Create new annotation and auto-create pending review"""
        from app.services.label_studio_service import LabelStudioService

        task = self.db.query(Task).filter(
            Task.id == annotation_data.task_id
        ).first()

        if not task:
            raise ValueError("Task not found")

        # Create annotation in DB
        new_annotation = Annotation(
            **annotation_data.model_dump(),
            annotator_id=annotator_id
        )
        self.db.add(new_annotation)
        self.db.flush()  # get annotation ID without committing

        # Auto-create a PENDING review so it appears in review queue
        pending_review = Review(
            annotation_id=new_annotation.id,
            status=ReviewStatus.PENDING,
            reviewer_id=None,        # not assigned yet
            comments=None,
            reviewed_at=None
        )
        self.db.add(pending_review)

        # Push to Label Studio if task has LS ID
        if task.label_studio_task_id:
            ls_service = LabelStudioService()
            try:
                ls_annotation = ls_service.create_annotation(
                    task_id=task.label_studio_task_id,
                    result=annotation_data.annotation_data.get("result", [])
                )
                new_annotation.label_studio_annotation_id = ls_annotation.get("id")
            except Exception as e:
                logger.warning(f"Failed to sync annotation to Label Studio: {e}")

        # Update task status to completed
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(new_annotation)
        return new_annotation

    # ... rest of the methods stay the same
    def get_annotation(self, annotation_id: UUID) -> Optional[Annotation]:
        return self.db.query(Annotation).filter(
            Annotation.id == annotation_id
        ).first()

    def get_task_annotations(self, task_id: UUID) -> List[Annotation]:
        return self.db.query(Annotation).filter(
            Annotation.task_id == task_id
        ).order_by(Annotation.version.desc()).all()

    def get_latest_annotation(self, task_id: UUID) -> Optional[Annotation]:
        return self.db.query(Annotation).filter(
            Annotation.task_id == task_id
        ).order_by(Annotation.version.desc()).first()

    def update_annotation(
        self,
        annotation_id: UUID,
        annotation_data: AnnotationUpdate
    ) -> Optional[Annotation]:
        existing = self.get_annotation(annotation_id)
        if not existing:
            return None

        new_version = Annotation(
            task_id=existing.task_id,
            annotator_id=existing.annotator_id,
            annotation_data=annotation_data.annotation_data or existing.annotation_data,
            time_spent=annotation_data.time_spent or existing.time_spent,
            version=existing.version + 1,
            label_studio_annotation_id=existing.label_studio_annotation_id
        )

        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)
        return new_version

    def get_user_annotations(self, user_id: UUID, limit: Optional[int] = None) -> List[Annotation]:
        query = self.db.query(Annotation).filter(
            Annotation.annotator_id == user_id
        ).order_by(Annotation.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_project_annotations(self, project_id: UUID) -> List[Annotation]:
        return self.db.query(Annotation).join(Task).filter(
            Task.project_id == project_id
        ).all()

    def get_annotation_stats(self, user_id: UUID) -> dict:
        from sqlalchemy import func
        total_annotations = self.db.query(func.count(Annotation.id)).filter(
            Annotation.annotator_id == user_id
        ).scalar()
        total_time = self.db.query(func.sum(Annotation.time_spent)).filter(
            Annotation.annotator_id == user_id
        ).scalar()
        avg_time = self.db.query(func.avg(Annotation.time_spent)).filter(
            Annotation.annotator_id == user_id
        ).scalar()
        return {
            "total_annotations": total_annotations or 0,
            "total_time_spent": total_time or 0,
            "average_time_per_annotation": float(avg_time) if avg_time else 0
        }