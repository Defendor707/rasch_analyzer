
import asyncio
import logging
import os
from typing import NoReturn
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application

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
    
    await application.run_polling(drop_pending_updates=True)


async def run_student_bot():
    """Run student bot"""
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
    
    await application.run_polling(drop_pending_updates=True)


async def main():
    """Run both bots concurrently"""
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
