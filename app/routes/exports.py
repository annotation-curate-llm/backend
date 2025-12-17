from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.export_job import ExportJob, ExportStatus
from app.schemas.export import ExportJobCreate, ExportJobResponse
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["Exports"])

@router.post("/", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_export_job(
    export_data: ExportJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Create a new export job (admin only)"""
    # Create export job
    export_job = ExportJob(
        project_id=export_data.project_id,
        created_by=current_user.id,
        export_format=export_data.export_format,
        status=ExportStatus.PENDING
    )
    db.add(export_job)
    db.commit()
    db.refresh(export_job)
    
    # Trigger background processing
    export_service = ExportService(db)
    background_tasks.add_task(export_service.process_export, export_job.id)
    
    return export_job

@router.get("/", response_model=List[ExportJobResponse])
def list_export_jobs(
    project_id: UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """List all export jobs (admin only)"""
    query = db.query(ExportJob)
    if project_id:
        query = query.filter(ExportJob.project_id == project_id)
    
    jobs = query.order_by(ExportJob.created_at.desc()).all()
    return jobs

@router.get("/{job_id}", response_model=ExportJobResponse)
def get_export_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get export job status"""
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_export_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Delete export job (admin only)"""
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    db.delete(job)
    db.commit()
    return None