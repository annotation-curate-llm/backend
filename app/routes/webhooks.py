from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.task import Task, TaskStatus
from app.models.annotation import Annotation
from app.models.review import Review, ReviewStatus
from app.services.label_studio_service import LabelStudioService
from datetime import datetime
from fastapi import Depends
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/annotation-complete")
async def annotation_complete(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Called by Label Studio when annotator submits annotation.
    Auto-marks task complete and creates pending review.
    """
    try:
        payload = await request.json()
        logger.info(f"Webhook received: {payload}")

        action = payload.get("action")

        # Only handle annotation created/updated events
        if action not in ["ANNOTATION_CREATED", "ANNOTATION_UPDATED"]:
            return {"status": "ignored", "action": action}

        # Extract data from payload
        annotation_data = payload.get("annotation", {})
        ls_task = payload.get("task", {})
        ls_task_id = ls_task.get("id")
        ls_annotation_id = annotation_data.get("id")
        result = annotation_data.get("result", [])

        if not ls_task_id:
            logger.warning("Webhook missing task ID")
            return {"status": "ignored", "reason": "no task id"}

        # Find the task in our DB by label_studio_task_id
        task = db.query(Task).filter(
            Task.label_studio_task_id == ls_task_id
        ).first()

        if not task:
            logger.warning(f"No task found for LS task ID: {ls_task_id}")
            return {"status": "ignored", "reason": "task not found"}

        # Skip if already completed
        if task.status in [TaskStatus.COMPLETED, TaskStatus.REVIEWED]:
            logger.info(f"Task {task.id} already completed, skipping")
            return {"status": "skipped", "reason": "already completed"}

        # Create annotation record in our DB
        new_annotation = Annotation(
            task_id=task.id,
            annotator_id=task.assigned_to,
            annotation_data={
                "result": result,
                "label_studio_annotation_id": ls_annotation_id
            },
            label_studio_annotation_id=ls_annotation_id,
            time_spent=annotation_data.get("lead_time", 0)
        )
        db.add(new_annotation)
        db.flush()

        # Auto-create pending review
        pending_review = Review(
            annotation_id=new_annotation.id,
            status=ReviewStatus.PENDING,
            reviewer_id=None,
            comments=None,
            reviewed_at=None
        )
        db.add(pending_review)

        # Update task status to completed
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()

        db.commit()
        logger.info(f"Task {task.id} auto-completed via webhook")

        return {"status": "success", "task_id": str(task.id)}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))