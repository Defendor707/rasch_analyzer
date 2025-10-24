
import asyncio
import logging
from bot.main import main as teacher_bot_main
from student_bot.main import main as student_bot_main

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def run_teacher_bot():
    """Run teacher bot"""
    try:
        logger.info("O'qituvchi boti ishga tushmoqda...")
        await teacher_bot_main()
    except Exception as e:
        logger.error(f"O'qituvchi botida xatolik: {e}")

async def run_student_bot():
    """Run student bot"""
    try:
        logger.info("Talabgor boti ishga tushmoqda...")
        await student_bot_main()
    except Exception as e:
        logger.error(f"Talabgor botida xatolik: {e}")

async def main():
    """Run both bots concurrently"""
    logger.info("Ikkala bot ham ishga tushmoqda...")
    
    # Run both bots concurrently
    await asyncio.gather(
        run_teacher_bot(),
        run_student_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())
