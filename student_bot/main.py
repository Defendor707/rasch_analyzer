
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
    help_command,
    handle_message,
    handle_callback_query
)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Uzr, xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )
        )


def main():
    """Start the student bot"""
    bot_token = os.getenv('STUDENT_BOT_TOKEN')
    
    if not bot_token:
        logger.error("STUDENT_BOT_TOKEN topilmadi! .env faylda STUDENT_BOT_TOKEN o'rnatilganligini tekshiring.")
        return
    
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("Talabgor boti ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()()
