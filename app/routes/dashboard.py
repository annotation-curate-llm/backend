from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Dict, List
from uuid import UUID
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.annotation import Annotation
from app.models.review import Review, ReviewStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Get overall system statistics (admin only)"""
    
    # Total counts
    total_users = db.query(func.count(User.id)).scalar()
    total_projects = db.query(func.count(Project.id)).filter(Project.is_active == True).scalar()
    total_tasks = db.query(func.count(Task.id)).scalar()
    total_annotations = db.query(func.count(Annotation.id)).scalar()
    
    # Task status breakdown
    task_status_counts = db.query(
        Task.status,
        func.count(Task.id)
    ).group_by(Task.status).all()
    
    task_stats = {
        "unassigned": 0,
        "assigned": 0,
        "in_progress": 0,
        "completed": 0,
        "reviewed": 0
    }
    for status, count in task_status_counts:
        task_stats[status.value] = count
    
    # Review statistics
    review_stats = db.query(
        Review.status,
        func.count(Review.id)
    ).group_by(Review.status).all()
    
    review_counts = {
        "pending": 0,
        "approved": 0,
        "rejected": 0
    }
    for status, count in review_stats:
        review_counts[status.value] = count
    
    # User role distribution
    user_roles = db.query(
        User.role,
        func.count(User.id)
    ).filter(User.is_active == True).group_by(User.role).all()
    
    role_distribution = {}
    for role, count in user_roles:
        role_distribution[role.value] = count
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_annotations = db.query(func.count(Annotation.id)).filter(
        Annotation.created_at >= seven_days_ago
    ).scalar()
    
    recent_tasks = db.query(func.count(Task.id)).filter(
        Task.created_at >= seven_days_ago
    ).scalar()
    
    return {
        "overview": {
            "total_users": total_users,
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "total_annotations": total_annotations
        },
        "task_statistics": task_stats,
        "review_statistics": review_counts,
        "user_distribution": role_distribution,
        "recent_activity": {
            "annotations_last_7_days": recent_annotations,
            "tasks_created_last_7_days": recent_tasks
        },
        "completion_rate": round((task_stats["completed"] / total_tasks * 100) if total_tasks > 0 else 0, 2)
    }


@router.get("/user-stats/{user_id}")
def get_user_statistics(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get statistics for a specific user"""
    
    # Verify access (user can see own stats, admin can see all)
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view these statistics")
    
    # Check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Tasks assigned to user
    total_tasks_assigned = db.query(func.count(Task.id)).filter(
        Task.assigned_to == user_id
    ).scalar()
    
    # Tasks completed
    tasks_completed = db.query(func.count(Task.id)).filter(
        Task.assigned_to == user_id,
        Task.status.in_([TaskStatus.COMPLETED, TaskStatus.REVIEWED])
    ).scalar()
    
    # Annotations created
    total_annotations = db.query(func.count(Annotation.id)).filter(
        Annotation.annotator_id == user_id
    ).scalar()
    
    # Average time spent
    avg_time = db.query(func.avg(Annotation.time_spent)).filter(
        Annotation.annotator_id == user_id
    ).scalar()
    
    # Reviews (if user is reviewer)
    reviews_given = 0
    if user.role == UserRole.REVIEWER or user.role == UserRole.ADMIN:
        reviews_given = db.query(func.count(Review.id)).filter(
            Review.reviewer_id == user_id
        ).scalar()
    
    # Annotations by review status
    approved_annotations = db.query(func.count(Annotation.id)).join(Review).filter(
        Annotation.annotator_id == user_id,
        Review.status == ReviewStatus.APPROVED
    ).scalar()
    
    rejected_annotations = db.query(func.count(Annotation.id)).join(Review).filter(
        Annotation.annotator_id == user_id,
        Review.status == ReviewStatus.REJECTED
    ).scalar()
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_annotations = db.query(func.count(Annotation.id)).filter(
        Annotation.annotator_id == user_id,
        Annotation.created_at >= thirty_days_ago
    ).scalar()
    
    return {
        "user_id": str(user_id),
        "user_name": user.name,
        "user_email": user.email,
        "user_role": user.role.value,
        "task_statistics": {
            "total_assigned": total_tasks_assigned or 0,
            "completed": tasks_completed or 0,
            "in_progress": (total_tasks_assigned or 0) - (tasks_completed or 0),
            "completion_rate": round((tasks_completed / total_tasks_assigned * 100) if total_tasks_assigned > 0 else 0, 2)
        },
        "annotation_statistics": {
            "total_annotations": total_annotations or 0,
            "approved": approved_annotations or 0,
            "rejected": rejected_annotations or 0,
            "approval_rate": round((approved_annotations / total_annotations * 100) if total_annotations > 0 else 0, 2),
            "average_time_seconds": round(float(avg_time)) if avg_time else 0
        },
        "review_statistics": {
            "reviews_given": reviews_given or 0
        },
        "recent_activity": {
            "annotations_last_30_days": recent_annotations or 0
        }
    }


@router.get("/project-analytics/{project_id}")
def get_project_analytics(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Get detailed analytics for a specific project (admin only)"""
    
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Task statistics
    total_tasks = db.query(func.count(Task.id)).filter(
        Task.project_id == project_id
    ).scalar()
    
    task_status_breakdown = db.query(
        Task.status,
        func.count(Task.id)
    ).filter(Task.project_id == project_id).group_by(Task.status).all()
    
    status_counts = {
        "unassigned": 0,
        "assigned": 0,
        "in_progress": 0,
        "completed": 0,
        "reviewed": 0
    }
    for status, count in task_status_breakdown:
        status_counts[status.value] = count
    
    # Annotator performance
    annotator_stats = db.query(
        User.id,
        User.name,
        User.email,
        func.count(Task.id).label('tasks_assigned'),
        func.count(case((Task.status == TaskStatus.COMPLETED, 1))).label('tasks_completed')
    ).join(Task, Task.assigned_to == User.id).filter(
        Task.project_id == project_id,
        User.role == UserRole.ANNOTATOR
    ).group_by(User.id, User.name, User.email).all()
    
    annotators = []
    for user_id, name, email, assigned, completed in annotator_stats:
        annotators.append({
            "user_id": str(user_id),
            "name": name,
            "email": email,
            "tasks_assigned": assigned,
            "tasks_completed": completed,
            "completion_rate": round((completed / assigned * 100) if assigned > 0 else 0, 2)
        })
    
    # Review statistics
    total_reviews = db.query(func.count(Review.id)).join(
        Annotation
    ).join(Task).filter(Task.project_id == project_id).scalar()
    
    approved_reviews = db.query(func.count(Review.id)).join(
        Annotation
    ).join(Task).filter(
        Task.project_id == project_id,
        Review.status == ReviewStatus.APPROVED
    ).scalar()
    
    # Progress over time (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_progress = db.query(
        func.date(Task.completed_at).label('date'),
        func.count(Task.id).label('completed_tasks')
    ).filter(
        Task.project_id == project_id,
        Task.completed_at >= thirty_days_ago,
        Task.status.in_([TaskStatus.COMPLETED, TaskStatus.REVIEWED])
    ).group_by(func.date(Task.completed_at)).order_by(func.date(Task.completed_at)).all()
    
    progress_timeline = [
        {
            "date": str(date),
            "completed_tasks": count
        }
        for date, count in daily_progress
    ]
    
    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "task_overview": {
            "total_tasks": total_tasks or 0,
            "status_breakdown": status_counts,
            "completion_percentage": round((status_counts["completed"] / total_tasks * 100) if total_tasks > 0 else 0, 2)
        },
        "annotator_performance": annotators,
        "review_statistics": {
            "total_reviews": total_reviews or 0,
            "approved": approved_reviews or 0,
            "approval_rate": round((approved_reviews / total_reviews * 100) if total_reviews > 0 else 0, 2)
        },
        "progress_timeline": progress_timeline
    }
