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

@router.get("/label-config-templates")
def get_label_config_templates():
    """Get predefined label configuration templates for different annotation types"""
    return {
        "image_classification": {
            "name": "Image Classification",
            "description": "Classify images into predefined categories",
            "category": "classification",
            "data_type": "image",
            "config": """<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image">
    <Choice value="Category1"/>
    <Choice value="Category2"/>
    <Choice value="Category3"/>
  </Choices>
</View>"""
        },
        "text_classification": {
            "name": "Text Classification",
            "description": "Classify text into sentiment or categories",
            "category": "classification",
            "data_type": "text",
            "config": """<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text">
    <Choice value="Positive"/>
    <Choice value="Negative"/>
    <Choice value="Neutral"/>
  </Choices>
</View>"""
        },
        "audio_classification": {
            "name": "Audio Classification",
            "description": "Classify audio files by emotion or category",
            "category": "classification",
            "data_type": "audio",
            "config": """<View>
  <Audio name="audio" value="$audio"/>
  <Choices name="emotion" toName="audio">
    <Choice value="Happy"/>
    <Choice value="Sad"/>
    <Choice value="Angry"/>
    <Choice value="Neutral"/>
  </Choices>
</View>"""
        },
        "object_detection": {
            "name": "Object Detection",
            "description": "Draw bounding boxes around objects in images",
            "category": "detection",
            "data_type": "image",
            "config": """<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="Person"/>
    <Label value="Car"/>
    <Label value="Animal"/>
    <Label value="Object"/>
  </RectangleLabels>
</View>"""
        },
        "named_entity_recognition": {
            "name": "Named Entity Recognition (NER)",
            "description": "Identify and label entities in text",
            "category": "ner",
            "data_type": "text",
            "config": """<View>
  <Text name="text" value="$text"/>
  <Labels name="label" toName="text">
    <Label value="Person"/>
    <Label value="Organization"/>
    <Label value="Location"/>
    <Label value="Date"/>
  </Labels>
</View>"""
        },
        "image_segmentation": {
            "name": "Image Segmentation",
            "description": "Draw polygons to segment objects in images",
            "category": "segmentation",
            "data_type": "image",
            "config": """<View>
  <Image name="image" value="$image"/>
  <PolygonLabels name="label" toName="image">
    <Label value="Foreground"/>
    <Label value="Background"/>
    <Label value="Object"/>
  </PolygonLabels>
</View>"""
        },
        "video_classification": {
            "name": "Video Classification",
            "description": "Classify video content",
            "category": "classification",
            "data_type": "video",
            "config": """<View>
  <Video name="video" value="$video"/>
  <Choices name="category" toName="video">
    <Choice value="Action"/>
    <Choice value="Comedy"/>
    <Choice value="Drama"/>
  </Choices>
</View>"""
        }
    }

@router.post("/{project_id}/assets/upload", status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(require_role([UserRole.ADMIN]))
):
    """Upload asset to project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    storage_service = StorageService()
    file_data = await storage_service.upload_file(file, str(project_id))
    
    asset = Asset(
        project_id=project_id,
        file_url=file_data["file_url"],
        file_path=file_data["file_path"],  # Add this
        file_name=file_data["file_name"],
        mime_type=file_data["mime_type"],
        file_size=file_data["file_size"]  # Add this
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

@router.get("/test-ls")
def test_label_studio():
    import httpx
    from app.core.config import settings
    
    url = f"{settings.LABEL_STUDIO_URL}/api/projects"
    headers = {"Authorization": f"Bearer {settings.LABEL_STUDIO_API_KEY}"}
    
    try:
        client = httpx.Client(timeout=30.0)
        response = client.get(url, headers=headers)
        return {
            "status_code": response.status_code,
            "url": url,
            "key_first_10": settings.LABEL_STUDIO_API_KEY[:10],
            "key_last_10": settings.LABEL_STUDIO_API_KEY[-10:],
            "response": response.json()
        }
    except Exception as e:
        return {"error": str(e), "url": url}