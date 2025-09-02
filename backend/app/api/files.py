import logging
import os
import shutil
import uuid
from tempfile import NamedTemporaryFile
from typing import Dict, Any
from pathlib import Path

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.models.file import File as FileModel
from app.models.file import FileResponse
from app.services.data_loader import load_and_validate_records
from app.services.storage import StorageService, get_storage_service
from fastapi.responses import FileResponse as FastAPIFileResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_validate(
    file: UploadFile = File(...),
    task_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload a file, save it using the configured storage service,
    create a file record in the database, and validate its contents.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in [".csv", ".xlsx"]:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    # Create a temporary file to store the upload
    try:
        with NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
    finally:
        file.file.close()

    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    try:
        # Upload to storage
        storage_path = storage.upload_file(
            file_path=tmp_path,
            file_name=unique_filename,
            content_type=file.content_type
        )
        
        # Validate data
        validation_results = load_and_validate_records(storage_path)
        
        # Create DB record
        file_record = FileModel(
            filename=unique_filename,
            original_filename=file.filename,
            storage_path=storage_path,
            file_type=file_extension.strip('.'),
            status="validated" if validation_results["is_valid"] else "error",
            validation_results=validation_results,
            task_id=task_id
        )
        
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        
        logger.info(f"File '{file.filename}' uploaded and validated for task {task_id}.")
        return file_record

    except Exception as e:
        logger.error(f"Failed to process file upload: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during file processing: {e}"
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.post("/upload-and-validate")
async def upload_and_validate_file(file: UploadFile = File(...)):
    """Uploads a CSV/XLSX, saves to uploads, and validates records for automation."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in {'.xlsx', '.xls', '.csv'}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Please use .csv or .xlsx."
        )

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.upload_dir, unique_filename)

    try:
        content = await file.read()
        # ✅ Check if the uploaded file is empty
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty."
            )
            
        with open(file_path, "wb") as f:
            f.write(content)

        # This call can now raise HTTPException directly for validation errors
        validation_data = load_and_validate_records(file_path)
        
        logger.info(f"File '{file.filename}' uploaded and validated successfully.")
        return {
            "message": "File validated successfully!",
            "filename": unique_filename,
            "original_filename": file.filename,
            "validation": validation_data
        }
    
    # ✅ Catch specific validation errors first
    except HTTPException as e:
        # If a validation error occurs, clean up the temp file and re-raise
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e
        
    # Catch any other unexpected errors
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"An unexpected error occurred during file validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}"
        )

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
        
        return FastAPIFileResponse(
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
