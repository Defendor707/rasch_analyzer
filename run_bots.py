
import asyncio
import logging
import os
from typing import NoReturn
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def run_teacher_bot():
    """Run teacher bot"""
    from bot.handlers.message_handlers import (
        start_command,
        help_command,
        sample_command,
        handle_document,
        handle_message,
        handle_callback_query
    )
    from bot.handlers.payment_handlers import (
        admin_panel_command,
        handle_admin_callbacks,
        show_payment_history,
        show_bot_balance,
        precheckout_callback,
        successful_payment_callback
    )
    from bot.utils.test_scheduler import check_and_finalize_expired_tests
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, filters, ContextTypes
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors caused by updates"""
        logger.error(f"Update {update} caused error {context.error}")
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Uzr, xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
            )
    
    bot_token = os.getenv('BOT_TOKEN')
    
    if not bot_token:
        logger.error("BOT_TOKEN topilmadi!")
        return
    
    logger.info("O'qituvchi boti ishga tushmoqda...")
    
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("namuna", sample_command))
    application.add_handler(CommandHandler("payments", show_payment_history))
    application.add_handler(CommandHandler("balance", show_bot_balance))
    application.add_handler(CommandHandler("admos", admin_panel_command))
    
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    application.add_handler(CallbackQueryHandler(handle_admin_callbacks, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("O'qituvchi boti ishga tushdi!")
    
    await application.initialize()
    await application.start()
    
    if application.updater is None:
        raise RuntimeError("Updater not available for polling")
    
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Wait a bit for student bot to initialize
    await asyncio.sleep(2)
    
    # Store student bot application in bot_data for access from handlers
    application.bot_data['student_bot_app'] = student_bot_app
    logger.info("Student bot application saqlandi")
    
    # Set up scheduler for checking expired tests
    scheduler = AsyncIOScheduler()
    
    # Run every hour to check for expired tests
    scheduler.add_job(
        check_and_finalize_expired_tests,
        trigger=IntervalTrigger(hours=1),
        args=[application],
        kwargs={'student_bot_app': student_bot_app},
        id='check_expired_tests',
        name='Check and finalize expired tests',
        replace_existing=True
    )
    
    # Also run immediately on startup
    scheduler.add_job(
        check_and_finalize_expired_tests,
        args=[application],
        kwargs={'student_bot_app': student_bot_app},
        id='check_expired_tests_startup',
        name='Check expired tests on startup'
    )
    
    scheduler.start()
    logger.info("Test scheduler ishga tushdi (har soatda tekshirish)")
    
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


async def run_student_bot():
    """Run student bot"""
    global student_bot_app
    
    from student_bot.handlers.student_handlers import (
        start_command,
        help_command,
        handle_message,
        handle_callback_query
    )
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    
    bot_token = os.getenv('STUDENT_BOT_TOKEN')
    
    if not bot_token:
        logger.error("STUDENT_BOT_TOKEN topilmadi!")
        return
    
    logger.info("Talabgor boti ishga tushmoqda...")
    
    application = Application.builder().token(bot_token).build()
    student_bot_app = application  # Store globally for scheduler
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors caused by updates"""
        logger.error(f"Update {update} caused error {context.error}")
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Uzr, xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
            )
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("Talabgor boti ishga tushdi!")
    
    await application.initialize()
    await application.start()
    
    if application.updater is None:
        raise RuntimeError("Updater not available for polling")
    
    await application.updater.start_polling(drop_pending_updates=True)
    
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


# Global variable to store student bot application
student_bot_app = None

async def main():
    """Run both bots concurrently"""
    global student_bot_app
    
    logger.info("Ikkala bot ham ishga tushmoqda...")
    
    # Create tasks for both bots
    teacher_task = asyncio.create_task(run_teacher_bot())
    student_task = asyncio.create_task(run_student_bot())
    
    # Wait for both tasks (they run indefinitely)
    try:
        await asyncio.gather(teacher_task, student_task)
    except KeyboardInterrupt:
        logger.info("Botlar to'xtatilmoqda...")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dastur to'xtatildi")
