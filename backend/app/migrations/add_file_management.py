import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings
from app.models.database import Base
from app.models.file import File
from app.models.task import Task
from app.models.execution import Execution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_migrations():
    """
    Applies necessary database migrations.
    This is a simple migration script for projects without Alembic.
    """
    logger.info("Starting database migration...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        logger.info("Creating all tables if they don't exist (Base.metadata.create_all)...")
        # This will create 'files' table and add new columns to existing tables
        # if they are not present. It's idempotent.
        await conn.run_sync(Base.metadata.create_all)
        
        # In a more complex scenario with existing data, you might need raw SQL:
        # await conn.execute(text('ALTER TABLE tasks ADD COLUMN script_path VARCHAR(255)'))
        
    logger.info("Database migration finished.")

if __name__ == "__main__":
    asyncio.run(apply_migrations())
