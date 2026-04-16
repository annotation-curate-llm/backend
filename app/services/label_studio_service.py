import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

class LabelStudioService:
    def __init__(self):
        self.base_url = settings.LABEL_STUDIO_URL
        self.headers = {
            "Authorization": f"Token {settings.LABEL_STUDIO_API_KEY}",
            "Content-Type": "application/json"
        }
        self.client = httpx.Client(timeout=30.0)  # Sync client
    
    def create_project(self, title: str, label_config: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/projects"
        data = {"title": title, "label_config": label_config}
        
        try:
            response = self.client.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Label Studio API error: {str(e)}")
    
    def import_task(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/projects/{project_id}/import"
        
        try:
            response = self.client.post(url, json=[data], headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to import task: {str(e)}")
    
    def get_task(self, task_id: int) -> Dict[str, Any]:
        url = f"{self.base_url}/api/tasks/{task_id}"
        
        try:
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get task: {str(e)}")
    
    def get_project_tasks(self, project_id: int) -> list:
        """Get all tasks for a project — used to retrieve task ID after import"""
        url = f"{self.base_url}/api/tasks?project={project_id}"
    
        try:
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            # LS returns {"tasks": [...]} or just [...]
            return data.get("tasks", data) if isinstance(data, dict) else data
        except httpx.HTTPError as e:
            raise Exception(f"Failed to get project tasks: {str(e)}")
    
    def create_annotation(self, task_id: int, result: list, completion_data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/tasks/{task_id}/annotations"
        data = {"result": result, **(completion_data or {})}
        
        try:
            response = self.client.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Failed to create annotation: {str(e)}")
    
    def close(self):
        self.client.close()