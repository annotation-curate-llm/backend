from supabase import create_client, Client
from fastapi import UploadFile
from app.core.config import settings
import uuid
from typing import Dict

class StorageService:
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.bucket = settings.STORAGE_BUCKET
    
    async def upload_file(self, file: UploadFile, project_id: str) -> Dict[str, str]:
        file_ext = file.filename.split(".")[-1].lower()
        unique_filename = f"{project_id}/{uuid.uuid4()}.{file_ext}"
        content = await file.read()

        response = self.supabase.storage.from_(self.bucket).upload(
            unique_filename,
            content,
            {"content-type": file.content_type}
        )

        public_url = self.supabase.storage.from_(self.bucket).get_public_url(unique_filename)

        # For text files, also read content directly
        text_content = None
        if file.content_type == "text/plain":
            try:
                text_content = content.decode("utf-8")
            except Exception:
                text_content = None

        return {
            "file_path": unique_filename,
            "file_url": public_url,
            "file_name": file.filename,
            "mime_type": file.content_type,
            "file_size": len(content),
            "text_content": text_content  # ADD THIS
        }
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from Supabase storage"""
        response = self.supabase.storage.from_(self.bucket).remove([file_path])
        return True
    def upload_bytes(
    self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload raw bytes to Supabase storage — used for exports"""
        self.supabase.storage.from_(bucket).upload(
            path,
            data,
            {"content-type": content_type}
        )
        public_url = self.supabase.storage.from_(bucket).get_public_url(path)
        return public_url