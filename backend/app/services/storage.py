from abc import ABC, abstractmethod
import os
from minio import Minio
from minio.error import S3Error
import logging
from datetime import timedelta

from app.config import settings

logger = logging.getLogger(__name__)

class StorageService(ABC):
    @abstractmethod
    def upload_file(self, file_path: str, file_name: str, content_type: str) -> str:
        pass

    @abstractmethod
    def get_presigned_url(self, file_path: str) -> str:
        pass

    @abstractmethod
    def download_file(self, file_path: str, destination_path: str):
        pass

class LocalStorage(StorageService):
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def upload_file(self, file_path: str, file_name: str, content_type: str) -> str:
        destination = os.path.join(self.upload_dir, file_name)
        os.rename(file_path, destination)
        return destination

    def get_presigned_url(self, file_path: str) -> str:
        # Local storage doesn't have presigned URLs, returns a local file path
        return f"file://{os.path.abspath(file_path)}"

    def download_file(self, file_path: str, destination_path: str):
        if os.path.exists(file_path):
            os.rename(file_path, destination_path)
        else:
            raise FileNotFoundError(f"File not found at {file_path}")

class MinioStorage(StorageService):
    def __init__(self):
        try:
            # Internal client for server-to-MinIO operations
            self.client_internal = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,
                region="us-east-1"
            )
            # Public client used only to construct presigned URLs for the browser
            public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
            self.client_public = Minio(
                public_endpoint,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,
                region="us-east-1"
            )
            self.bucket_name = settings.MINIO_BUCKET_NAME
            self.ensure_bucket_exists()
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise

    def ensure_bucket_exists(self):
        try:
            found = self.client_internal.bucket_exists(self.bucket_name)
            if not found:
                self.client_internal.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created.")
        except S3Error as e:
            logger.error(f"Error checking or creating bucket: {e}")
            raise

    def upload_file(self, file_path: str, file_name: str, content_type: str) -> str:
        try:
            self.client_internal.fput_object(
                self.bucket_name, file_name, file_path, content_type=content_type
            )
            return file_name
        except S3Error as e:
            logger.error(f"Failed to upload {file_name} to MinIO: {e}")
            raise

    def get_presigned_url(self, file_path: str) -> str:
        try:
            return self.client_public.presigned_get_object(
                self.bucket_name, file_path, expires=timedelta(hours=1)
            )
        except S3Error as e:
            logger.error(f"Failed to get presigned URL for {file_path}: {e}")
            raise

    def download_file(self, file_path: str, destination_path: str):
        try:
            self.client_internal.fget_object(self.bucket_name, file_path, destination_path)
        except S3Error as e:
            logger.error(f"Failed to download {file_path} from MinIO: {e}")
            raise

def get_storage_service() -> StorageService:
    if settings.STORAGE_BACKEND == "minio":
        return MinioStorage()
    else:
        return LocalStorage()
