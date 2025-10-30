import logging
import sys
import os
from telegram import Update
from telegram.ext import ContextTypes

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.utils.earnings_manager import EarningsManager
from student_bot.handlers.student_handlers import start_test

logger = logging.getLogger(__name__)
earnings_manager = EarningsManager()


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query for test payments"""
    query = update.pre_checkout_query
    await query.answer(ok=True)
    logger.info(f"Pre-checkout approved: {query.invoice_payload}")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful test payment"""
    payment_info = update.message.successful_payment
    user_id = update.effective_user.id
    
    # Get pending test payment info
    pending_payment = context.user_data.get('pending_test_payment', {})
    test_id = pending_payment.get('test_id')
    price = pending_payment.get('price', 0)
    teacher_id = pending_payment.get('teacher_id')
    
    if not test_id or not teacher_id:
        await update.message.reply_text(
            "❌ To'lov ma'lumotlarini topib bo'lmadi. "
            "Iltimos, o'qituvchingizga murojaat qiling."
        )
        return
    
    # Record earnings for teacher
    try:
        earning = earnings_manager.record_test_payment(
            teacher_id=teacher_id,
            student_id=str(user_id),
            test_id=test_id,
            amount=price,
            payment_id=payment_info.telegram_payment_charge_id
        )
        
        # Mark test as paid for this student
        if 'paid_tests' not in context.user_data:
            context.user_data['paid_tests'] = {}
        context.user_data['paid_tests'][test_id] = True
        
        logger.info(
            f"Test to'lovi muvaffaqiyatli: "
            f"Student {user_id}, Test {test_id}, Amount {price}, "
            f"Teacher share: {earning['teacher_share']}"
        )
        
        await update.message.reply_text(
            f"✅ To'lov muvaffaqiyatli qabul qilindi!\n\n"
            f"💰 To'langan: {price} ⭐ Stars\n\n"
            f"Testni boshlash uchun 'start_test_{test_id}' buyrug'ini yuboring "
            f"yoki qayta urinib ko'ring."
        )
        
        # Clear pending payment
        context.user_data['pending_test_payment'] = {}
        
        # Automatically start the test after payment
        await start_test(update, context, test_id)
        
    except Exception as e:
        logger.error(f"To'lovni qayd qilishda xatolik: {e}")
        await update.message.reply_text(
            "❌ To'lovni qayd qilishda xatolik yuz berdi. "
            "Iltimos, o'qituvchingizga murojaat qiling."
        )
