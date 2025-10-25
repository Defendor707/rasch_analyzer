import logging
from telegram import Update, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils.payment_manager import PaymentManager

logger = logging.getLogger(__name__)
payment_manager = PaymentManager()


async def create_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 file_name: str):
    """Create and send payment invoice for file analysis"""
    config = payment_manager.get_config()
    price_stars = config['analysis_price_stars']
    
    title = "📊 Rasch tahlili"
    description = f"Fayl tahlili: {file_name}\n\nTo'lovdan keyin PDF hisobot yuboriladi."
    payload = f"analysis_{update.effective_user.id}_{file_name}"
    
    prices = [LabeledPrice("Rasch tahlili", price_stars)]
    
    try:
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ To'lov qilish", pay=True)]
            ])
        )
        
        context.user_data['pending_payment_file'] = file_name
        
    except Exception as e:
        logger.error(f"Invoice yaratishda xatolik: {e}")
        await update.message.reply_text(
            "❌ To'lov tizimida xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
        )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query (validate payment before processing)"""
    query = update.pre_checkout_query
    
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment"""
    payment_info = update.message.successful_payment
    user_id = update.effective_user.id
    
    file_name = context.user_data.get('pending_payment_file', 'Unknown')
    
    payment_id = payment_manager.record_payment(
        user_id=user_id,
        amount_stars=payment_info.total_amount,
        telegram_payment_charge_id=payment_info.telegram_payment_charge_id,
        file_name=file_name
    )
    
    logger.info(f"To'lov muvaffaqiyatli: User {user_id}, File: {file_name}, Stars: {payment_info.total_amount}")
    
    await update.message.reply_text(
        f"✅ To'lov muvaffaqiyatli qabul qilindi!\n\n"
        f"💰 Summa: {payment_info.total_amount} ⭐ Stars\n"
        f"📄 Fayl: {file_name}\n\n"
        f"⏳ Tahlil jarayoni boshlanmoqda..."
    )
    
    context.user_data['payment_completed'] = True
    context.user_data['paid_file_name'] = file_name


async def show_payment_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's payment history"""
    user_id = update.effective_user.id
    payments = payment_manager.get_user_payments(user_id)
    
    if not payments:
        await update.message.reply_text(
            "📊 To'lovlar tarixi bo'sh.\n\n"
            "Hali birorta tahlil uchun to'lov qilmagansiz."
        )
        return
    
    message = "💳 To'lovlar tarixi:\n\n"
    
    for i, payment in enumerate(reversed(payments[-10:]), 1):
        timestamp = payment['timestamp'][:10]
        file_name = payment.get('file_name', 'N/A')
        amount = payment['amount_stars']
        
        message += f"{i}. 📅 {timestamp}\n"
        message += f"   📄 {file_name}\n"
        message += f"   💰 {amount} ⭐ Stars\n\n"
    
    await update.message.reply_text(message)


async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment statistics (admin only)"""
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
        return
    
    stats = payment_manager.get_payment_stats()
    config = payment_manager.get_config()
    
    message = (
        f"📊 To'lovlar statistikasi\n\n"
        f"💰 Jami to'lovlar: {stats['total_payments']} ta\n"
        f"⭐ Jami Stars: {stats['total_stars']}\n"
        f"👥 Foydalanuvchilar: {stats['unique_users']} ta\n\n"
        f"💵 Joriy narx: {config['analysis_price_stars']} ⭐ Stars\n"
    )
    
    if stats['latest_payment']:
        latest = stats['latest_payment']
        message += f"\n🕐 So'nggi to'lov:\n"
        message += f"   📅 {latest['timestamp'][:16]}\n"
        message += f"   👤 User ID: {latest['user_id']}\n"
        message += f"   💰 {latest['amount_stars']} Stars\n"
    
    await update.message.reply_text(message)


async def update_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update analysis price (admin only)"""
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Noto'g'ri format!\n\n"
            "Foydalanish: /setprice <Stars miqdori>\n"
            "Misol: /setprice 150"
        )
        return
    
    try:
        new_price = int(context.args[0])
        if new_price <= 0:
            raise ValueError("Narx musbat bo'lishi kerak")
        
        payment_manager.update_price(new_price)
        
        await update.message.reply_text(
            f"✅ Narx yangilandi!\n\n"
            f"Yangi narx: {new_price} ⭐ Stars"
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri qiymat! Faqat musbat raqam kiriting."
        )
