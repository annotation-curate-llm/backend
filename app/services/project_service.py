from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.label_studio_service import LabelStudioService
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.ls_service = LabelStudioService()
    
    def create_project(
        self, 
        project_data: ProjectCreate, 
        user_id: UUID
    ) -> Project:
        """Create new project with Label Studio integration"""
        # Create project in Label Studio
        ls_project = self.ls_service.create_project(
            title=project_data.name,
            label_config=project_data.label_config
        )
        
        # Create project in database
        new_project = Project(
            **project_data.model_dump(),
            created_by=user_id,
            label_studio_project_id=ls_project.get("id")
        )
        self.db.add(new_project)
        self.db.commit()
        self.db.refresh(new_project)
        return new_project
    
    def get_project(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID"""
        return self.db.query(Project).filter(Project.id == project_id).first()
    
    def get_all_projects(self, user_id: Optional[UUID] = None) -> List[Project]:
        """Get all projects, optionally filtered by user"""
        query = self.db.query(Project).filter(Project.is_active == True)
        if user_id:
            query = query.filter(Project.created_by == user_id)
        return query.order_by(Project.created_at.desc()).all()
    
    def update_project(
        self, 
        project_id: UUID, 
        project_data: ProjectUpdate
    ) -> Optional[Project]:
        """Update project"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        for key, value in project_data.model_dump(exclude_unset=True).items():
            setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(project)
        return project
    
    def delete_project(self, project_id: UUID) -> bool:
        """Soft delete project"""
        project = self.get_project(project_id)
        if not project:
            return False
        
        project.is_active = False
        project.updated_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def get_project_stats(self, project_id: UUID) -> Dict:
        """Get project statistics"""
        total_tasks = self.db.query(func.count(Task.id)).filter(
            Task.project_id == project_id
        ).scalar()
        
        completed_tasks = self.db.query(func.count(Task.id)).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.COMPLETED
        ).scalar()
        
        in_progress_tasks = self.db.query(func.count(Task.id)).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.IN_PROGRESS
        ).scalar()
        
        unassigned_tasks = self.db.query(func.count(Task.id)).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.UNASSIGNED
        ).scalar()
        
        reviewed_tasks = self.db.query(func.count(Task.id)).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.REVIEWED
        ).scalar()
        
        return {
            "total_tasks": total_tasks or 0,
            "completed_tasks": completed_tasks or 0,
            "in_progress_tasks": in_progress_tasks or 0,
            "unassigned_tasks": unassigned_tasks or 0,
            "reviewed_tasks": reviewed_tasks or 0,
            "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }