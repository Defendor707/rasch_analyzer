
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from student_bot.handlers.student_handlers import (
    start_command,
    restart_command,
    help_command,
    handle_message,
    handle_callback_query
)
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.utils.error_notifier import error_notifier

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if context.error:
        await error_notifier.notify_error(
            context=context,
            error=context.error,
            update=update if isinstance(update, Update) else None,
            custom_message="Talabgor botida xatolik"
        )
    
    if update and isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Uzr, xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


async def main():
    """Start the student bot"""
    bot_token = os.getenv('STUDENT_BOT_TOKEN')
    
    if not bot_token:
        logger.error("STUDENT_BOT_TOKEN topilmadi! .env faylda STUDENT_BOT_TOKEN o'rnatilganligini tekshiring.")
        return
    
    # Admin IDs ni payment_config.json dan o'qish
    import json
    try:
        with open('data/payment_config.json', 'r') as f:
            config = json.load(f)
            admin_ids = config.get('admin_ids', [])
            error_notifier.set_admin_ids(admin_ids)
            logger.info(f"Talabgor bot error notifier sozlandi. Admin IDs: {admin_ids}")
    except Exception as e:
        logger.warning(f"Admin IDs yuklanmadi: {e}")
    
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ishlayapti")

    
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("Talabgor boti ishga tushdi...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
