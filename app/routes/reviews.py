from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.review import Review, ReviewStatus
from app.models.annotation import Annotation
from app.models.task import Task, TaskStatus
from app.models.asset import Asset
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewWithAnnotation

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.get("/pending", response_model=List[ReviewWithAnnotation])
def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.REVIEWER, UserRole.ADMIN]))
):
    """Get all pending reviews"""
    # Query annotations that need review
    results = db.query(
        Review,
        Annotation,
        Task,
        Asset
    ).join(
        Annotation, Review.annotation_id == Annotation.id
    ).join(
        Task, Annotation.task_id == Task.id
    ).join(
        Asset, Task.asset_id == Asset.id
    ).filter(
        Review.status == ReviewStatus.PENDING
    ).all()
    
    response = []
    for review, annotation, task, asset in results:
        review_dict = ReviewWithAnnotation.model_validate(review).model_dump()
        review_dict["task_id"] = task.id
        review_dict["annotator_id"] = annotation.annotator_id
        review_dict["annotation_data"] = annotation.annotation_data
        review_dict["file_url"] = asset.file_url
        review_dict["file_name"] = asset.file_name
        response.append(ReviewWithAnnotation(**review_dict))
    
    return response

@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.REVIEWER, UserRole.ADMIN]))
):
    """Create a review for an annotation"""
    # Verify annotation exists
    annotation = db.query(Annotation).filter(
        Annotation.id == review_data.annotation_id
    ).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    # Create review
    new_review = Review(
        annotation_id=review_data.annotation_id,
        reviewer_id=current_user.id,
        status=review_data.status,
        comments=review_data.comments,
        reviewed_at=datetime.utcnow()
    )
    db.add(new_review)
    
    # Update task status based on review
    task = db.query(Task).filter(Task.id == annotation.task_id).first()
    if review_data.status == ReviewStatus.APPROVED:
        task.status = TaskStatus.REVIEWED
    elif review_data.status == ReviewStatus.REJECTED:
        task.status = TaskStatus.ASSIGNED  # Reassign to annotator
    
    db.commit()
    db.refresh(new_review)
    return new_review

@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get review by ID"""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review