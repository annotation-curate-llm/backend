from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.task import Task, TaskStatus
from app.models.asset import Asset
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.label_studio_service import LabelStudioService
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.ls_service = LabelStudioService()
    
    def create_task(
        self, 
        task_data: TaskCreate,
        label_studio_project_id: Optional[int] = None
    ) -> Task:
        """Create new task"""
        new_task = Task(**task_data.model_dump())
        self.db.add(new_task)
        self.db.flush()  # Get task ID without committing
        
        # Import to Label Studio if project ID provided
        if label_studio_project_id:
            asset = self.db.query(Asset).filter(
                Asset.id == task_data.asset_id
            ).first()
            
            if asset:
                ls_task = self.ls_service.import_task(
                    project_id=label_studio_project_id,
                    data={"image": asset.file_url}  # Adjust based on asset type
                )
                new_task.label_studio_task_id = ls_task.get("id")
        
        self.db.commit()
        self.db.refresh(new_task)
        return new_task
    
    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID"""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get_user_tasks(
        self, 
        user_id: UUID, 
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """Get tasks assigned to user"""
        query = self.db.query(Task).filter(Task.assigned_to == user_id)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.priority.desc(), Task.created_at).all()
    
    def get_next_task(self, user_id: UUID) -> Optional[Task]:
        """Get next available task for user"""
        return self.db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.status == TaskStatus.ASSIGNED
        ).order_by(
            Task.priority.desc(), 
            Task.created_at
        ).first()
    
    def update_task(
        self, 
        task_id: UUID, 
        task_data: TaskUpdate
    ) -> Optional[Task]:
        """Update task"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        for key, value in task_data.model_dump(exclude_unset=True).items():
            setattr(task, key, value)
        
        # Update timestamps based on status changes
        if task_data.status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.utcnow()
        elif task_data.status == TaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.utcnow()
        
        task.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def assign_tasks(
        self, 
        project_id: UUID, 
        user_id: UUID, 
        count: int = 10
    ) -> int:
        """Assign multiple tasks to user"""
        tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.UNASSIGNED
        ).limit(count).all()
        
        assigned_count = 0
        for task in tasks:
            task.assigned_to = user_id
            task.status = TaskStatus.ASSIGNED
            task.assigned_at = datetime.utcnow()
            assigned_count += 1
        
        self.db.commit()
        return assigned_count
    
    def auto_assign_tasks(
        self, 
        project_id: UUID, 
        tasks_per_user: int = 5
    ) -> Dict[UUID, int]:
        """Auto-assign tasks to available annotators"""
        # Get available annotators (users with role 'annotator')
        annotators = self.db.query(User).filter(
            User.role == "annotator",
            User.is_active == True
        ).all()
        
        if not annotators:
            return {}
        
        # Get unassigned tasks
        unassigned_tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.UNASSIGNED
        ).all()
        
        assignment_map = {}
        task_index = 0
        
        # Round-robin assignment
        for annotator in annotators:
            assigned_count = 0
            while assigned_count < tasks_per_user and task_index < len(unassigned_tasks):
                task = unassigned_tasks[task_index]
                task.assigned_to = annotator.id
                task.status = TaskStatus.ASSIGNED
                task.assigned_at = datetime.utcnow()
                assigned_count += 1
                task_index += 1
            
            assignment_map[annotator.id] = assigned_count
        
        self.db.commit()
        return assignment_map
    
    def get_project_tasks(
        self, 
        project_id: UUID,
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """Get all tasks for a project"""
        query = self.db.query(Task).filter(Task.project_id == project_id)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.priority.desc(), Task.created_at).all()
    
    def bulk_update_status(
        self, 
        task_ids: List[UUID], 
        status: TaskStatus
    ) -> int:
        """Bulk update task status"""
        updated_count = self.db.query(Task).filter(
            Task.id.in_(task_ids)
        ).update(
            {Task.status: status, Task.updated_at: datetime.utcnow()},
            synchronize_session=False
        )
        self.db.commit()
        return updated_count