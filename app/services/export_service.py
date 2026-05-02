import json
import zipfile
import csv
from io import BytesIO, StringIO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.export_job import ExportJob, ExportStatus, ExportFormat
from app.models.annotation import Annotation
from app.models.review import Review, ReviewStatus
from app.models.task import Task
from app.models.asset import Asset
from app.services.storage_service import StorageService
import logging

logger = logging.getLogger(__name__)

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
            job.status = ExportStatus.PROCESSING
            self.db.commit()

            # Fetch approved annotations only
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

            if not annotations:
                raise Exception("No approved annotations found for this project")

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

            # Create ZIP file with export + labels.csv always included
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f'export.{job.export_format.value.lower()}', data)

                # Always include a simple labels.csv for quick ML use
                if job.export_format != ExportFormat.CSV:
                    labels_csv = self.build_labels_csv(annotations)
                    zip_file.writestr('labels.csv', labels_csv)

                # Include README
                zip_file.writestr('README.txt', self.build_readme(job.export_format, annotations))

            # Upload to Supabase
            zip_buffer.seek(0)
            file_path = f"exports/{job.project_id}/{job.id}.zip"

            try:
                file_url = self.storage_service.upload_bytes(
                    bucket="exports",
                    path=file_path,
                    data=zip_buffer.read(),
                    content_type="application/zip"
                )
            except Exception as e:
                raise Exception(f"Failed to upload export file: {str(e)}")

            # Update job as completed
            job.status = ExportStatus.COMPLETED
            job.file_url = file_url
            job.total_annotations = len(annotations)
            job.completed_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            self.db.commit()
            logger.error(f"Export job {job_id} failed: {str(e)}")

    # ─── Core Parser ────────────────────────────────────────────────────────────

    def parse_annotation_result(self, result: list, asset) -> dict:
        """Parse Label Studio result into clean format based on annotation type"""
        if not result:
            return {"annotation_type": "unknown", "label": None}

        first = result[0]
        result_type = first.get("type", "")

        # Image Classification
        if result_type == "choices":
            choices = first.get("value", {}).get("choices", [])
            return {
                "annotation_type": "classification",
                "label": choices[0] if choices else None,
                "all_labels": choices
            }

        # Object Detection (Bounding Boxes)
        elif result_type == "rectanglelabels":
            boxes = []
            for r in result:
                value = r.get("value", {})
                boxes.append({
                    "label": value.get("rectanglelabels", [None])[0],
                    "x": value.get("x"),
                    "y": value.get("y"),
                    "width": value.get("width"),
                    "height": value.get("height"),
                    "rotation": value.get("rotation", 0)
                })
            return {
                "annotation_type": "object_detection",
                "bounding_boxes": boxes
            }

        # Segmentation (Polygons)
        elif result_type == "polygonlabels":
            polygons = []
            for r in result:
                value = r.get("value", {})
                polygons.append({
                    "label": value.get("polygonlabels", [None])[0],
                    "points": value.get("points", [])
                })
            return {
                "annotation_type": "segmentation",
                "polygons": polygons
            }

        # NER (Text Labels)
        elif result_type == "labels":
            entities = []
            for r in result:
                value = r.get("value", {})
                entities.append({
                    "label": value.get("labels", [None])[0],
                    "start": value.get("start"),
                    "end": value.get("end"),
                    "text": value.get("text")
                })
            return {
                "annotation_type": "ner",
                "entities": entities
            }

        # Audio Classification
        elif result_type == "taxonomy":
            choices = first.get("value", {}).get("taxonomy", [])
            return {
                "annotation_type": "audio_classification",
                "label": choices[0][0] if choices else None
            }

        else:
            return {
                "annotation_type": result_type,
                "raw": result
            }

    # ─── Export Builders ─────────────────────────────────────────────────────────

    def build_json_export(self, annotations):
        """Build JSON format export — works for all annotation types"""
        data = []
        for annotation in annotations:
            task = annotation.task
            asset = task.asset
            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, asset)

            data.append({
                "annotation_id": str(annotation.id),
                "task_id": str(annotation.task_id),
                "annotator_id": str(annotation.annotator_id),
                "image_url": asset.file_url,
                "image_name": asset.file_name,
                **parsed,
                "raw_result": result,
                "created_at": annotation.created_at.isoformat()
            })
        return json.dumps(data, indent=2)

    def build_jsonl_export(self, annotations):
        """Build JSONL format — one JSON object per line"""
        lines = []
        for annotation in annotations:
            task = annotation.task
            asset = task.asset
            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, asset)

            lines.append(json.dumps({
                "annotation_id": str(annotation.id),
                "task_id": str(annotation.task_id),
                "annotator_id": str(annotation.annotator_id),
                "image_url": asset.file_url,
                "image_name": asset.file_name,
                **parsed,
                "raw_result": result,
                "created_at": annotation.created_at.isoformat()
            }))
        return "\n".join(lines)

    def build_csv_export(self, annotations):
        """Build CSV format — handles all annotation types"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "image_name", "image_url", "annotation_type",
            "label", "x", "y", "width", "height",
            "points", "entity_text", "entity_start", "entity_end",
            "annotator_id", "created_at"
        ])

        for annotation in annotations:
            task = annotation.task
            asset = task.asset
            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, asset)
            ann_type = parsed.get("annotation_type")

            if ann_type == "classification":
                writer.writerow([
                    asset.file_name, asset.file_url, ann_type,
                    parsed.get("label"), "", "", "", "",
                    "", "", "", "",
                    str(annotation.annotator_id),
                    annotation.created_at.isoformat()
                ])

            elif ann_type == "object_detection":
                for box in parsed.get("bounding_boxes", []):
                    writer.writerow([
                        asset.file_name, asset.file_url, ann_type,
                        box["label"], box["x"], box["y"],
                        box["width"], box["height"],
                        "", "", "", "",
                        str(annotation.annotator_id),
                        annotation.created_at.isoformat()
                    ])

            elif ann_type == "segmentation":
                for poly in parsed.get("polygons", []):
                    writer.writerow([
                        asset.file_name, asset.file_url, ann_type,
                        poly["label"], "", "", "", "",
                        str(poly["points"]), "", "", "",
                        str(annotation.annotator_id),
                        annotation.created_at.isoformat()
                    ])

            elif ann_type == "ner":
                for entity in parsed.get("entities", []):
                    writer.writerow([
                        asset.file_name, asset.file_url, ann_type,
                        entity["label"], "", "", "", "",
                        "", entity["text"],
                        entity["start"], entity["end"],
                        str(annotation.annotator_id),
                        annotation.created_at.isoformat()
                    ])

            else:
                writer.writerow([
                    asset.file_name, asset.file_url, ann_type,
                    "", "", "", "", "",
                    "", "", "", "",
                    str(annotation.annotator_id),
                    annotation.created_at.isoformat()
                ])

        return output.getvalue()

    def build_labels_csv(self, annotations):
        """Build simple labels.csv always included in ZIP for quick ML use"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["image_name", "image_url", "label", "annotation_type"])

        for annotation in annotations:
            task = annotation.task
            asset = task.asset
            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, asset)
            ann_type = parsed.get("annotation_type")

            if ann_type == "classification":
                writer.writerow([
                    asset.file_name, asset.file_url,
                    parsed.get("label"), ann_type
                ])
            elif ann_type == "object_detection":
                for box in parsed.get("bounding_boxes", []):
                    writer.writerow([
                        asset.file_name, asset.file_url,
                        box["label"], ann_type
                    ])
            elif ann_type == "segmentation":
                for poly in parsed.get("polygons", []):
                    writer.writerow([
                        asset.file_name, asset.file_url,
                        poly["label"], ann_type
                    ])
            elif ann_type == "ner":
                for entity in parsed.get("entities", []):
                    writer.writerow([
                        asset.file_name, asset.file_url,
                        entity["label"], ann_type
                    ])

        return output.getvalue()

    def build_coco_export(self, annotations):
        """Build COCO format — for object detection"""
        images = []
        coco_annotations = []
        categories = set()

        image_id = 1
        annotation_id = 1

        for annotation in annotations:
            task = annotation.task
            asset = task.asset

            images.append({
                "id": image_id,
                "file_name": asset.file_name,
                "url": asset.file_url,
                "width": 0,
                "height": 0
            })

            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, asset)

            for box in parsed.get("bounding_boxes", []):
                label = box["label"]
                if label:
                    categories.add(label)
                    cat_list = sorted(categories)

                    coco_annotations.append({
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": cat_list.index(label) + 1,
                        "bbox": [
                            box["x"], box["y"],
                            box["width"], box["height"]
                        ],
                        "area": box["width"] * box["height"],
                        "iscrowd": 0
                    })
                    annotation_id += 1

            image_id += 1

        return json.dumps({
            "info": {"description": "Exported from Curate LLM"},
            "images": images,
            "annotations": coco_annotations,
            "categories": [
                {"id": i + 1, "name": cat}
                for i, cat in enumerate(sorted(categories))
            ]
        }, indent=2)

    def build_yolo_export(self, annotations):
        """Build YOLO format — for object detection"""
        lines = []
        all_labels = []

        # First pass — collect all labels for class mapping
        for annotation in annotations:
            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, annotation.task.asset)
            for box in parsed.get("bounding_boxes", []):
                if box["label"] and box["label"] not in all_labels:
                    all_labels.append(box["label"])

        all_labels = sorted(all_labels)

        # Second pass — build YOLO lines
        for annotation in annotations:
            result = annotation.annotation_data.get("result", [])
            parsed = self.parse_annotation_result(result, annotation.task.asset)

            for box in parsed.get("bounding_boxes", []):
                if box["label"]:
                    class_id = all_labels.index(box["label"])
                    # Convert percentage to normalized (0-1)
                    x_center = (box["x"] + box["width"] / 2) / 100
                    y_center = (box["y"] + box["height"] / 2) / 100
                    w = box["width"] / 100
                    h = box["height"] / 100
                    lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

        # Add classes.txt content at top as comment
        class_comments = "\n".join([f"# {i}: {l}" for i, l in enumerate(all_labels)])
        return class_comments + "\n" + "\n".join(lines)

    def build_readme(self, export_format, annotations) -> str:
        """Build README.txt explaining the export structure"""
        ann_types = set()
        for annotation in annotations:
            result = annotation.annotation_data.get("result", [])
            if result:
                ann_types.add(result[0].get("type", "unknown"))

        return f"""Curate LLM — Annotation Export
================================
Export Format: {export_format.value}
Total Annotations: {len(annotations)}
Annotation Types: {', '.join(ann_types) if ann_types else 'unknown'}
Exported At: {datetime.utcnow().isoformat()}

Files Included:
- export.{export_format.value.lower()} — Full annotation data
- labels.csv — Simple image→label mapping for quick ML use

How to use labels.csv for training:
  import pandas as pd
  df = pd.read_csv('labels.csv')
  # df has columns: image_name, image_url, label, annotation_type
  # Download images using image_url and use label as the target

For object detection (COCO/YOLO):
  - Coordinates are in percentage (0-100) in JSON
  - Normalized (0-1) in YOLO format

Support: https://curate-llm.vercel.app
"""