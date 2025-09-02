from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App
    app_name: str = "Automation Studio"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    timezone: str = "America/New_York"
    
    # Database
    database_url: str = "postgresql://admin:password@postgres:5432/automation"
    
    # VNC
    vnc_host: str = "vnc"
    vnc_display: str = ":1"
    vnc_port: int = 5901
    vnc_web_port: int = 7900
    
    # VNC Security (for production)
    vnc_password: Optional[str] = None  # Set via environment variable
    vnc_require_auth: bool = False  # Enable in production
    
    # Public hostname for VNC
    vnc_public_host: Optional[str] = None  # e.g., "automation.mycompany.com"
    
    # Storage
    upload_dir: str = "/app/uploads"
    screenshot_dir: str = "/app/screenshots"
    max_upload_size: int = 10485760  # 10MB
    
    # Playwright
    playwright_headless: bool = False  # MUST be False for VNC visibility
    playwright_timeout: int = 30000
    playwright_viewport_width: int = 1920
    playwright_viewport_height: int = 1080
    
    # WebSocket
    ws_heartbeat_interval: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create directories
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.screenshot_dir, exist_ok=True)
