"""
Database jadvallarini yaratish uchun skript
"""
import asyncio
import logging
from dotenv import load_dotenv
from bot.database.connection import db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database():
    """Database ni sozlash va jadvallarni yaratish"""
    try:
        logger.info("Database sozlanmoqda...")
        
        # Database ga ulanish
        await db.initialize()
        logger.info("Database ulanishi muvaffaqiyatli!")
        
        # Jadvallarni yaratish
        await db.create_tables()
        logger.info("Barcha jadvallar yaratildi!")
        
        # Health check
        is_healthy = await db.health_check()
        if is_healthy:
            logger.info("✅ Database to'liq tayyor va ishlayapti!")
        else:
            logger.error("❌ Database health check muvaffaqiyatsiz")
        
        await db.close()
        
    except Exception as e:
        logger.error(f"Database sozlashda xatolik: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(setup_database())
