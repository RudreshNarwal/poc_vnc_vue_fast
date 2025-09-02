from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
import os
import uuid
import logging
import pandas as pd
from pathlib import Path

from app.config import settings
from app.services.data_loader import load_and_validate_records

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.txt', '.json'}
ALLOWED_MIME_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'text/plain',
    'application/json'
}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file (Excel, CSV, etc.) for automation prerequisites"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        content = await file.read()
        if len(content) > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size / 1024 / 1024:.1f}MB"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Try to parse file for preview
        preview_data = None
        try:
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, nrows=5)
                preview_data = {
                    "columns": df.columns.tolist(),
                    "sample_rows": df.head().to_dict('records'),
                    "total_rows": len(pd.read_excel(file_path))
                }
            elif file_ext == '.csv':
                df = pd.read_csv(file_path, nrows=5)
                preview_data = {
                    "columns": df.columns.tolist(),
                    "sample_rows": df.head().to_dict('records'),
                    "total_rows": len(pd.read_csv(file_path))
                }
        except Exception as e:
            logger.warning(f"Could not parse file for preview: {str(e)}")
        
        logger.info(f"File uploaded: {file.filename} -> {unique_filename}")
        
        return {
            "filename": unique_filename,
            "original_filename": file.filename,
            "size": len(content),
            "content_type": file.content_type,
            "url": f"/uploads/{unique_filename}",
            "preview": preview_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )

@router.post("/upload-and-validate")
async def upload_and_validate_file(file: UploadFile = File(...)):
    """Uploads a CSV/XLSX, saves to uploads, and validates records for automation."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in {'.xlsx', '.xls', '.csv'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed. Please use .csv or .xlsx.")

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.upload_dir, unique_filename)

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        validation = load_and_validate_records(file_path)
        logger.info(f"File '{file.filename}' uploaded and validated successfully.")
        return {
            "message": "File validated successfully!",
            "filename": unique_filename,
            "original_filename": file.filename,
            "validation": validation
        }
    except HTTPException as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Validation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download an uploaded file"""
    try:
        file_path = os.path.join(settings.upload_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File download failed: {str(e)}"
        )

@router.get("/list")
async def list_files():
    """List all uploaded files"""
    try:
        files = []
        
        if os.path.exists(settings.upload_dir):
            for filename in os.listdir(settings.upload_dir):
                file_path = os.path.join(settings.upload_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "created": stat.st_ctime,
                        "url": f"/uploads/{filename}"
                    })
        
        return {"files": files}
        
    except Exception as e:
        logger.error(f"File listing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File listing failed: {str(e)}"
        )

@router.delete("/{filename}")
async def delete_file(filename: str):
    """Delete an uploaded file"""
    try:
        file_path = os.path.join(settings.upload_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        os.remove(file_path)
        logger.info(f"File deleted: {filename}")
        
        return {"message": f"File {filename} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File deletion failed: {str(e)}"
        )
