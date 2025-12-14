import httpx
from typing import Dict, Any, Optional
from app.config import settings

class LabelStudioService:
    def __init__(self):
        self.base_url = settings.LABEL_STUDIO_URL
        self.api_key = settings.LABEL_STUDIO_API_KEY
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_project(self, title: str, label_config: str) -> Dict[str, Any]:
        """Create project in Label Studio"""
        url = f"{self.base_url}/api/projects"
        data = {
            "title": title,
            "label_config": label_config
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    def import_task(
        self, 
        project_id: int, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Import task into Label Studio project"""
        url = f"{self.base_url}/api/projects/{project_id}/import"
        
        with httpx.Client() as client:
            response = client.post(url, json=[data], headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    def get_task(self, task_id: int) -> Dict[str, Any]:
        """Get task from Label Studio"""
        url = f"{self.base_url}/api/tasks/{task_id}"
        
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    def create_annotation(
        self,
        task_id: int,
        result: list,
        completion_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create annotation in Label Studio"""
        url = f"{self.base_url}/api/tasks/{task_id}/annotations"
        data = {
            "result": result,
            **(completion_data or {})
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()