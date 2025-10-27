import os
import logging
import traceback
import html
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class ErrorNotifier:
    """Xatoliklar haqida admin ga Telegram orqali xabarnoma yuborish"""
    
    def __init__(self, admin_ids: list | None = None):
        """
        Args:
            admin_ids: Admin foydalanuvchilar ID ro'yxati
        """
        self.admin_ids = admin_ids or []
        
    def set_admin_ids(self, admin_ids: list):
        """Admin IDlarni yangilash"""
        self.admin_ids = admin_ids
        
    async def notify_error(
        self, 
        context: ContextTypes.DEFAULT_TYPE,
        error: Exception,
        update: Update | None = None,
        custom_message: str | None = None
    ):
        """
        Admin ga xatolik haqida xabarnoma yuborish
        
        Args:
            context: Telegram context
            error: Xatolik obyekti
            update: Update obyekti (agar mavjud bo'lsa)
            custom_message: Qo'shimcha xabar
        """
        if not self.admin_ids:
            logger.warning("Admin IDlari o'rnatilmagan, xatolik xabarnomasi yuborilmadi")
            return
            
        # Xatolik haqida batafsil ma'lumot
        error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = html.escape(type(error).__name__)
        error_message = html.escape(str(error))
        error_traceback = ''.join(traceback.format_tb(error.__traceback__))
        
        # User ma'lumotlari
        user_info = "N/A"
        chat_info = "N/A"
        message_text = "N/A"
        
        if update:
            if update.effective_user:
                username = html.escape(update.effective_user.username or 'N/A')
                user_info = f"@{username} (ID: {update.effective_user.id})"
            if update.effective_chat:
                chat_type = html.escape(update.effective_chat.type)
                chat_info = f"{chat_type} (ID: {update.effective_chat.id})"
            if update.effective_message and update.effective_message.text:
                message_text = html.escape(update.effective_message.text[:100])  # Birinchi 100 ta belgi
        
        # Xabarnoma matni (barcha dinamik qiymatlar HTML-escaped)
        notification = f"""
🚨 <b>XATOLIK YUZAGA KELDI!</b>

⏰ <b>Vaqt:</b> {error_time}
❌ <b>Xatolik turi:</b> {error_type}
📝 <b>Xabar:</b> {error_message}

👤 <b>Foydalanuvchi:</b> {user_info}
💬 <b>Chat:</b> {chat_info}
📨 <b>Xabar matni:</b> {message_text}
"""
        
        if custom_message:
            escaped_custom = html.escape(custom_message)
            notification += f"\n💡 <b>Qo'shimcha:</b> {escaped_custom}"
            
        # Traceback ni alohida yuborish (juda uzun bo'lishi mumkin)
        # HTML pre tag ichida, shuning uchun escape qilish kerak
        escaped_traceback = html.escape(error_traceback[:3000])  # Max 3000 belgi
        traceback_msg = f"<pre>{escaped_traceback}</pre>"
        
        # Barcha adminlarga yuborish
        for admin_id in self.admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=notification,
                    parse_mode='HTML'
                )
                
                # Traceback ni alohida yuborish (agar mavjud bo'lsa)
                if error_traceback:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"📋 <b>Traceback:</b>\n{traceback_msg}",
                        parse_mode='HTML'
                    )
                    
                logger.info(f"Xatolik haqida admin {admin_id} ga xabarnoma yuborildi")
                
            except TelegramError as e:
                logger.error(f"Admin {admin_id} ga xabarnoma yuborishda xatolik: {e}")
    
    async def notify_critical(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        message: str
    ):
        """
        Muhim hodisalar haqida adminlarga xabar yuborish
        
        Args:
            context: Telegram context
            message: Xabar matni
        """
        if not self.admin_ids:
            return
            
        # HTML escape qilish (agar message HTML belgilarni o'z ichiga olsa)
        escaped_message = html.escape(message)
        
        notification = f"""
🔴 <b>MUHIM XABARNOMA</b>

⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{escaped_message}
"""
        
        for admin_id in self.admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=notification,
                    parse_mode='HTML'
                )
            except TelegramError as e:
                logger.error(f"Admin {admin_id} ga muhim xabar yuborishda xatolik: {e}")


# Global error notifier instance
error_notifier = ErrorNotifier()
