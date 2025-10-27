"""
PostgreSQL Database Connection Manager
Async database ulanish va operatsiyalarni boshqarish
"""
import os
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from bot.database.schema import Base

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """PostgreSQL database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self._initialized = False
        
    async def initialize(self):
        """Database ulanishini boshlash"""
        if self._initialized:
            return
            
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable topilmadi!")
        
        # PostgreSQL URL ni asyncpg uchun o'zgartirish
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif not database_url.startswith('postgresql+asyncpg://'):
            database_url = f'postgresql+asyncpg://{database_url}'
        
        # asyncpg sslmode parametrini qabul qilmaydi, uni olib tashlaymiz
        if '?sslmode=' in database_url:
            database_url = database_url.split('?sslmode=')[0]
        
        logger.info(f"Database ga ulanilmoqda...")
        
        # Engine yaratish
        self.engine = create_async_engine(
            database_url,
            echo=False,  # SQL querylarni log qilish (development da True qilish mumkin)
            pool_pre_ping=True,  # Ulanishni tekshirish
            pool_recycle=300,  # 5 daqiqada bir marta connection yangilash
        )
        
        # Session maker
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self._initialized = True
        logger.info("Database ulanishi muvaffaqiyatli!")
        
    async def create_tables(self):
        """Barcha jadvallarni yaratish"""
        if not self._initialized:
            await self.initialize()
        
        if not self.engine:
            raise RuntimeError("Database engine mavjud emas!")
            
        logger.info("Database jadvallari yaratilmoqda...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database jadvallari muvaffaqiyatli yaratildi!")
        
    async def drop_tables(self):
        """DIQQAT: Barcha jadvallarni o'chirish!"""
        if not self._initialized:
            await self.initialize()
        
        if not self.engine:
            raise RuntimeError("Database engine mavjud emas!")
            
        logger.warning("DIQQAT: Barcha jadvallar o'chirilmoqda...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
        logger.info("Barcha jadvallar o'chirildi")
        
    def get_session(self) -> AsyncSession:
        """Yangi session olish"""
        if not self._initialized or not self.session_maker:
            raise RuntimeError("Database initialize qilinmagan! Avval initialize() ni chaqiring")
        
        return self.session_maker()
    
    async def health_check(self) -> bool:
        """Database ulanishini tekshirish"""
        try:
            if not self._initialized:
                await self.initialize()
                
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Database ulanishini yopish"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database ulanishi yopildi")


# Global database instance
db = DatabaseConnection()
