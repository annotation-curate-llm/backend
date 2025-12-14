import json
import zipfile
from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.export_job import ExportJob, ExportStatus, ExportFormat
from app.models.annotation import Annotation
from app.models.review import Review, ReviewStatus
from app.models.task import Task
from app.models.asset import Asset
from app.services.storage_service import StorageService

class ExportService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = StorageService()
    
    def process_export(self, job_id: str):
        """Process export job in background"""
        job = self.db.query(ExportJob).filter(ExportJob.id == job_id).first()
        if not job:
            return
        
        try:
            # Update status
            job.status = ExportStatus.PROCESSING
            self.db.commit()
            
            # Fetch approved annotations
            annotations = self.db.query(Annotation).join(
                Review
            ).join(
                Task
            ).join(
                Asset
            ).filter(
                Review.status == ReviewStatus.APPROVED,
                Task.project_id == job.project_id
            ).all()
            
            # Build export based on format
            if job.export_format == ExportFormat.JSON:
                data = self.build_json_export(annotations)
            elif job.export_format == ExportFormat.JSONL:
                data = self.build_jsonl_export(annotations)
            elif job.export_format == ExportFormat.COCO:
                data = self.build_coco_export(annotations)
            elif job.export_format == ExportFormat.YOLO:
                data = self.build_yolo_export(annotations)
            elif job.export_format == ExportFormat.CSV:
                data = self.build_csv_export(annotations)
            else:
                raise ValueError(f"Unsupported format: {job.export_format}")
            
            # Create ZIP file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f'export.{job.export_format.value}', data)
            
            zip_buffer.seek(0)
            
            # Upload to storage
            file_path = f"exports/{job.project_id}/{job.id}.zip"
            # TODO: Implement upload to Supabase Storage
            # file_url = self.storage_service.upload_bytes(file_path, zip_buffer.read())
            file_url = f"https://storage.example.com/{file_path}"  # Placeholder
            
            # Update job
            job.status = ExportStatus.COMPLETED
            job.file_url = file_url
            job.total_annotations = len(annotations)
            job.completed_at = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            self.db.commit()
    
    def build_json_export(self, annotations):
        """Build JSON format export"""
        data = []
        for annotation in annotations:
            data.append({
                "annotation_id": str(annotation.id),
                "task_id": str(annotation.task_id),
                "annotator_id": str(annotation.annotator_id),
                "annotation_data": annotation.annotation_data,
                "created_at": annotation.created_at.isoformat()
            })
        return json.dumps(data, indent=2)
    
    def build_jsonl_export(self, annotations):
        """Build JSONL format export (one JSON per line)"""
        lines = []
        for annotation in annotations:
            lines.append(json.dumps({
                "annotation_id": str(annotation.id),
                "task_id": str(annotation.task_id),
                "annotation_data": annotation.annotation_data
            }))
        return "\n".join(lines)
    
    def build_coco_export(self, annotations):
        """Build COCO format export"""
        images = []
        coco_annotations = []
        categories = set()
        
        image_id = 1
        annotation_id = 1
        
        for annotation in annotations:
            task = annotation.task
            asset = task.asset
            
            # Add image
            images.append({
                "id": image_id,
                "file_name": asset.file_name,
                "width": 0,  # TODO: Extract from metadata
                "height": 0
            })
            
            # Process annotations
            for result in annotation.annotation_data.get("result", []):
                if result.get("type") == "rectanglelabels":
                    value = result["value"]
                    labels = value.get("rectanglelabels", [])
                    
                    for label in labels:
                        categories.add(label)
                        
                        coco_annotations.append({
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": list(categories).index(label) + 1,
                            "bbox": [
                                value["x"],
                                value["y"],
                                value["width"],
                                value["height"]
                            ],
                            "area": value["width"] * value["height"],
                            "iscrowd": 0
                        })
                        annotation_id += 1
            
            image_id += 1
        
        coco_data = {
            "images": images,
            "annotations": coco_annotations,
            "categories": [
                {"id": i + 1, "name": cat}
                for i, cat in enumerate(sorted(categories))
            ]
        }
        
        return json.dumps(coco_data, indent=2)
    
    def build_yolo_export(self, annotations):
        """Build YOLO format export"""
        # YOLO format: class_id x_center y_center width height (normalized)
        lines = []
        for annotation in annotations:
            for result in annotation.annotation_data.get("result", []):
                if result.get("type") == "rectanglelabels":
                    value = result["value"]
                    # Assuming normalized coordinates
                    x_center = value["x"] + value["width"] / 2
                    y_center = value["y"] + value["height"] / 2
                    
                    lines.append(
                        f"0 {x_center} {y_center} {value['width']} {value['height']}"
                    )
        
        return "\n".join(lines)
    
    def build_csv_export(self, annotations):
        """Build CSV format export"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "annotation_id",
            "task_id",
            "annotator_id",
            "label",
            "x",
            "y",
            "width",
            "height",
            "created_at"
        ])
        
        # Data
        for annotation in annotations:
            for result in annotation.annotation_data.get("result", []):
                if result.get("type") == "rectanglelabels":
                    value = result["value"]
                    for label in value.get("rectanglelabels", []):
                        writer.writerow([
                            str(annotation.id),
                            str(annotation.task_id),
                            str(annotation.annotator_id),
                            label,
                            value["x"],
                            value["y"],
                            value["width"],
                            value["height"],
                            annotation.created_at.isoformat()
                        ])
        
        return output.getvalue()