"""
Sertifikat yuborish funksiyasini qo'lda test qilish
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from bot.database.connection import db
from bot.utils.test_scheduler import send_test_results_to_students, process_and_send_test_results
from telegram.ext import Application

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_certificate_sending():
    """
    Test qilingan natijalar uchun sertifikat yuborish
    """
    try:
        # Database initialize
        await db.initialize()
        
        # Test ID ni olish
        from sqlalchemy import select
        from bot.database.schema import Test
        
        async with db.get_session() as session:
            result = await session.execute(
                select(Test).order_by(Test.created_at.desc()).limit(1)
            )
            test = result.scalar_one_or_none()
            
            if not test:
                logger.error("Test topilmadi!")
                return
            
            test_id = test.test_id
            logger.info(f"Test topildi: {test_id} - {test.title}")
        
        # Bot application yaratish (student bot)
        student_bot_token = os.getenv('STUDENT_BOT_TOKEN')
        teacher_bot_token = os.getenv('BOT_TOKEN')
        
        if not student_bot_token or not teacher_bot_token:
            logger.error("Bot tokenlar topilmadi!")
            return
        
        # Student bot app
        student_bot_app = Application.builder().token(student_bot_token).build()
        await student_bot_app.initialize()
        
        # Teacher bot app
        teacher_bot_app = Application.builder().token(teacher_bot_token).build()
        await teacher_bot_app.initialize()
        
        logger.info("Botlar initialize qilindi")
        
        # Test natijalarini yuborish
        logger.info(f"\nTest {test_id} uchun sertifikatlar yuborilmoqda...")
        
        # Test natijalarini process qilish va yuborish
        await process_and_send_test_results(
            application=teacher_bot_app,
            test_id=test_id,
            student_bot_app=student_bot_app
        )
        
        logger.info("✅ Jarayon yakunlandi!")
        
        # Cleanup
        await student_bot_app.shutdown()
        await teacher_bot_app.shutdown()
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


if __name__ == '__main__':
    asyncio.run(test_certificate_sending())
