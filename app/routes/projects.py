from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import require_role
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate, ProjectWithStats
from app.services.label_studio_service import LabelStudioService
from fastapi import UploadFile, File
from app.services.storage_service import StorageService
from app.models.asset import Asset

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_role([UserRole.ADMIN]))
):
    """Create new project (admin only)"""
    
    label_studio_project_id = None
    
    # Try to create in Label Studio (optional)
    try:
        ls_service = LabelStudioService()
        ls_project = ls_service.create_project(
            title=project_data.name,
            label_config=project_data.label_config
        )
        label_studio_project_id = ls_project.get("id")
    except Exception as e:
        # Log the error but continue
        print(f"Warning: Could not create Label Studio project: {e}")
        print("Creating project without Label Studio integration")
    
    # Create project in database
    new_project = Project(
        **project_data.model_dump(),
        created_by=current_user.id,
        label_studio_project_id=label_studio_project_id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@router.get("/", response_model=List[ProjectWithStats])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects with statistics"""
    projects = db.query(Project).filter(Project.is_active == True).all()
    
    result = []
    for project in projects:
        total = db.query(func.count(Task.id)).filter(Task.project_id == project.id).scalar()
        completed = db.query(func.count(Task.id)).filter(
            Task.project_id == project.id,
            Task.status == TaskStatus.COMPLETED
        ).scalar()
        pending = total - completed
        
        project_dict = ProjectWithStats.model_validate(project).model_dump()
        project_dict["total_tasks"] = total
        project_dict["completed_tasks"] = completed
        project_dict["pending_tasks"] = pending
        result.append(ProjectWithStats(**project_dict))
    
    return result

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project by ID"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/{project_id}/assets/upload", status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Upload asset to project"""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Upload to Supabase
    storage_service = StorageService()
    file_data = await storage_service.upload_file(file, str(project_id))
    
    # Create asset record
    asset = Asset(
        project_id=project_id,
        file_url=file_data["file_url"],
        file_name=file_data["file_name"],
        mime_type=file_data["mime_type"],
        uploaded_by=current_user.id
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return {"message": "Asset uploaded", "asset_id": str(asset.id), "file_url": file_data["file_url"]}

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Update project (admin only)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for key, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Delete project (admin only)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return None