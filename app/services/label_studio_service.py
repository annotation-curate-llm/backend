import httpx
import logging
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class LabelStudioService:
    def __init__(self):
        self.base_url = settings.LABEL_STUDIO_URL
        self.headers = {
            "Authorization": f"Token {settings.LABEL_STUDIO_API_KEY}",
            "Content-Type": "application/json"
        }
        # Increased timeout for Render cold starts
        self.client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=60.0)
        )
    
    def create_project(self, title: str, label_config: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/projects"
        data = {"title": title, "label_config": label_config}
        
        try:
            response = self.client.post(url, json=data, headers=self.headers)
            logger.info(f"LS create_project status: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Label Studio API error: {str(e)}")
    
    def import_task(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/projects/{project_id}/import"
        
        try:
            response = self.client.post(url, json=[data], headers=self.headers)
            logger.info(f"LS import_task status: {response.status_code}, body: {response.text}")
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
    
    def get_project_tasks(self, project_id: int) -> List:
        url = f"{self.base_url}/api/tasks?project={project_id}"
    
        try:
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
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
    
    def create_webhook(self, project_id: int, url: str) -> Dict[str, Any]:
        """Auto-add webhook to a Label Studio project"""
        webhook_url = f"{self.base_url}/api/webhooks"
        data = {
            "project": project_id,
            "url": url,
            "send_payload": True,
            "send_for_all_actions": False,
            "actions": ["ANNOTATION_CREATED", "ANNOTATION_UPDATED"]
        }
        try:
            response = self.client.post(webhook_url, json=data, headers=self.headers)
            logger.info(f"Webhook created for project {project_id}: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.warning(f"Failed to create webhook for project {project_id}: {e}")
            return {}
    
    def close(self):
        self.client.close()