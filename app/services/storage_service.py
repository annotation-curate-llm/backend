from supabase import create_client, Client
from fastapi import UploadFile
from app.config import settings
import uuid
from typing import Dict

class StorageService:
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.bucket = settings.STORAGE_BUCKET
    
    async def upload_file(
        self, 
        file: UploadFile,
        project_id: str
    ) -> Dict[str, str]:
        """Upload file to Supabase storage"""
        # Generate unique filename
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{project_id}/{uuid.uuid4()}.{file_ext}"
        
        # Read file content
        content = await file.read()
        
        # Upload to Supabase
        response = self.supabase.storage.from_(self.bucket).upload(
            unique_filename,
            content,
            {"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = self.supabase.storage.from_(self.bucket).get_public_url(unique_filename)
        
        return {
            "file_path": unique_filename,
            "file_url": public_url,
            "file_name": file.filename,
            "mime_type": file.content_type,
            "file_size": len(content)
        }
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from Supabase storage"""
        response = self.supabase.storage.from_(self.bucket).remove([file_path])
        return True