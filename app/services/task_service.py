from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.models.task import Task, TaskStatus
from app.models.asset import Asset
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.label_studio_service import LabelStudioService
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.ls_service = LabelStudioService()
    
    def create_task(
        self, 
        task_data: TaskCreate,
        label_studio_project_id: Optional[int] = None
    ) -> Task:
        """Create new task with optional Label Studio integration"""
        try:
            new_task = Task(**task_data.model_dump())
            self.db.add(new_task)
            self.db.flush()  # Get task ID without committing
            
            # Import to Label Studio if project ID provided
            if label_studio_project_id:
                asset = self.db.query(Asset).filter(
                    Asset.id == task_data.asset_id
                ).first()
    
                if asset:
                    try:
                        # Import task to Label Studio
                        ls_response = self.ls_service.import_task(
                            project_id=label_studio_project_id,
                            data={"image": asset.file_url}
                        )

                        logger.info(f"LS import response: {ls_response}")

                        # This version of LS doesn't return task_ids directly
                        # Verify import succeeded then find task by matching file URL
                        if ls_response.get("task_count", 0) > 0:
                            ls_tasks = self.ls_service.get_project_tasks(label_studio_project_id)
                            
                            if ls_tasks:
                                # Match by file URL to avoid race conditions
                                matching_task = next(
                                    (t for t in ls_tasks if t.get("data", {}).get("image") == asset.file_url),
                                    None
                                )
                                if matching_task:
                                    new_task.label_studio_task_id = matching_task.get("id")
                                    new_task.label_studio_project_id = label_studio_project_id
                                    logger.info(f"Task {new_task.id} linked to LS task {matching_task.get('id')}")
                                else:
                                    raise Exception(f"Could not find matching task in Label Studio after import. URL: {asset.file_url}")
                            else:
                                raise Exception("No tasks found in Label Studio project after import")
                        else:
                            raise Exception(f"Label Studio import failed. Response: {ls_response}")
                
                    except Exception as ls_error:
                        logger.error(f"Failed to import task to Label Studio: {str(ls_error)}")
                        self.db.rollback()
                        raise Exception(f"Failed to create task in Label Studio: {str(ls_error)}")
            
            self.db.commit()
            self.db.refresh(new_task)
            return new_task
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create task: {str(e)}")
            raise
    
    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID"""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get_task_with_asset(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID with asset data"""
        return self.db.query(Task).options(
            joinedload(Task.asset)
        ).filter(Task.id == task_id).first()
    
    def get_user_tasks(
        self, 
        user_id: UUID, 
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks assigned to user with pagination"""
        query = self.db.query(Task).options(
            joinedload(Task.asset)
        ).filter(Task.assigned_to == user_id)
        
        if status:
            query = query.filter(Task.status == status)
        
        return query.order_by(
            Task.priority.desc(), 
            Task.created_at
        ).offset(skip).limit(limit).all()
    
    def get_next_task(self, user_id: UUID) -> Optional[Task]:
        """Get next available task for user"""
        return self.db.query(Task).options(
            joinedload(Task.asset)
        ).filter(
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
        """Update task with automatic timestamp management"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        update_data = task_data.model_dump(exclude_unset=True)
        
        # Handle status-based timestamp updates
        if 'status' in update_data:
            new_status = update_data['status']
            
            if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.utcnow()
            elif new_status == TaskStatus.COMPLETED and not task.completed_at:
                task.completed_at = datetime.utcnow()
        
        # Apply all updates
        for key, value in update_data.items():
            setattr(task, key, value)
        
        try:
            self.db.commit()
            self.db.refresh(task)
            return task
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update task {task_id}: {str(e)}")
            raise
    
    def assign_tasks(
        self, 
        project_id: UUID, 
        user_id: UUID, 
        count: int = 10
    ) -> int:
        """Assign multiple tasks to user with locking to prevent race conditions"""
        if count < 1:
            raise ValueError("count must be at least 1")
        
        try:
            # Only assign tasks that are properly linked to Label Studio
            tasks = self.db.query(Task).filter(
                Task.project_id == project_id,
                Task.status == TaskStatus.UNASSIGNED,
                Task.label_studio_task_id.isnot(None)  # guard added
            ).with_for_update().limit(count).all()
            
            assigned_count = 0
            now = datetime.utcnow()
            
            for task in tasks:
                task.assigned_to = user_id
                task.status = TaskStatus.ASSIGNED
                task.assigned_at = now
                assigned_count += 1
            
            self.db.commit()
            return assigned_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to assign tasks: {str(e)}")
            raise
    
    def auto_assign_tasks(
        self, 
        project_id: UUID, 
        tasks_per_user: int = 5
    ) -> Dict[UUID, int]:
        """Auto-assign tasks to available annotators with validation"""
        if tasks_per_user < 1:
            raise ValueError("tasks_per_user must be at least 1")
        
        try:
            # Get available annotators
            annotators = self.db.query(User).filter(
                User.role == UserRole.ANNOTATOR,
                User.is_active == True
            ).all()
            
            if not annotators:
                logger.warning("No active annotators found for auto-assignment")
                return {}
            
            # Only assign tasks properly linked to Label Studio
            unassigned_tasks = self.db.query(Task).filter(
                Task.project_id == project_id,
                Task.status == TaskStatus.UNASSIGNED,
                Task.label_studio_task_id.isnot(None)  # guard added
            ).with_for_update().all()
            
            if not unassigned_tasks:
                logger.info("No unassigned tasks available")
                return {}
            
            assignment_map = {}
            task_index = 0
            now = datetime.utcnow()
            
            # Round-robin assignment
            for annotator in annotators:
                assigned_count = 0
                while assigned_count < tasks_per_user and task_index < len(unassigned_tasks):
                    task = unassigned_tasks[task_index]
                    task.assigned_to = annotator.id
                    task.status = TaskStatus.ASSIGNED
                    task.assigned_at = now
                    assigned_count += 1
                    task_index += 1
                
                assignment_map[annotator.id] = assigned_count
            
            self.db.commit()
            logger.info(f"Auto-assigned {task_index} tasks to {len(annotators)} annotators")
            return assignment_map
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to auto-assign tasks: {str(e)}")
            raise
    
    def get_project_tasks(
        self, 
        project_id: UUID,
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        """Get all tasks for a project with pagination"""
        query = self.db.query(Task).filter(Task.project_id == project_id)
        
        if status:
            query = query.filter(Task.status == status)
        
        return query.order_by(
            Task.priority.desc(), 
            Task.created_at
        ).offset(skip).limit(limit).all()
    
    def bulk_update_status(
        self, 
        task_ids: List[UUID], 
        status: TaskStatus
    ) -> int:
        """Bulk update task status"""
        if not task_ids:
            return 0
        
        try:
            updated_count = self.db.query(Task).filter(
                Task.id.in_(task_ids)
            ).update(
                {Task.status: status},
                synchronize_session=False
            )
            self.db.commit()
            return updated_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to bulk update task status: {str(e)}")
            raise
    
    def verify_task_access(
        self, 
        task_id: UUID, 
        user_id: UUID, 
        user_role: UserRole
    ) -> bool:
        """Verify if user has access to task"""
        task = self.get_task(task_id)
        
        if not task:
            return False
        
        # Admins can access all tasks
        if user_role == UserRole.ADMIN:
            return True
        
        # Users can only access their assigned tasks
        return task.assigned_to == user_id