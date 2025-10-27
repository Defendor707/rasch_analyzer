import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)
from bot.handlers.message_handlers import (
    start_command,
    help_command,
    sample_command,
    handle_document,
    handle_message,
    handle_callback_query
)
from bot.handlers.payment_handlers import (
    precheckout_callback,
    successful_payment_callback,
    show_payment_history,
    show_bot_balance,
    admin_panel_command
)
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
            update=update if isinstance(update, Update) else None
        )
    
    if update and isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Uzr, xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


async def main():
    """Start the bot"""
    bot_token = os.getenv('BOT_TOKEN')
    
    if not bot_token:
        logger.error("BOT_TOKEN topilmadi! .env faylda BOT_TOKEN o'rnatilganligini tekshiring.")
        return
    
    from bot.utils.payment_manager import PaymentManager
    payment_manager = PaymentManager()
    config = payment_manager.load_config()
    admin_ids = config.get('admin_ids', [])
    error_notifier.set_admin_ids(admin_ids)
    logger.info(f"Error notifier sozlandi. Admin IDs: {admin_ids}")
    
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("namuna", sample_command))
    application.add_handler(CommandHandler("payments", show_payment_history))
    application.add_handler(CommandHandler("balance", show_bot_balance))
    application.add_handler(CommandHandler("admos", admin_panel_command))
    
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    from bot.handlers.payment_handlers import handle_admin_callbacks
    application.add_handler(CallbackQueryHandler(handle_admin_callbacks, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    application.add_handler(MessageHandler(
        filters.Document.ALL,
        handle_document
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("O'qituvchi boti ishga tushdi...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
