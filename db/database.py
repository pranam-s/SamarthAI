from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(class_=AsyncSession, autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session