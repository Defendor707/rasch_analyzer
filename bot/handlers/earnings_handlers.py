import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils.earnings_manager import EarningsManager

logger = logging.getLogger(__name__)
earnings_manager = EarningsManager()


async def show_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'qituvchining balansini ko'rsatish"""
    user_id = update.effective_user.id
    balance = earnings_manager.get_teacher_balance(str(user_id))
    earnings = earnings_manager.get_teacher_earnings(str(user_id))
    
    message = (
        f"💰 *Sizning balans*\n\n"
        f"📊 Umumiy daromad: {balance['total_earned']} ⭐\n"
        f"💵 Mavjud: {balance['available']} ⭐\n"
        f"⏳ Kutilmoqda: {balance['pending']} ⭐\n"
        f"✅ Yechib olingan: {balance['withdrawn']} ⭐\n\n"
        f"📝 Jami to'lovlar: {len(earnings)} ta\n\n"
        f"💡 *Eslatma:*\n"
        f"Testlaringizdan kelgan daromadning 80% sizga tegishli.\n"
        f"Minimal yechib olish miqdori: 10 ⭐"
    )
    
    keyboard = []
    
    if balance['available'] >= 10:
        keyboard.append([
            InlineKeyboardButton("💸 Pul yechib olish", callback_data="withdraw_money")
        ])
    
    keyboard.append([
        InlineKeyboardButton("📜 Daromadlar tarixi", callback_data="earnings_history")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def show_earnings_history(query, context: ContextTypes.DEFAULT_TYPE):
    """Daromadlar tarixini ko'rsatish"""
    user_id = query.from_user.id
    earnings = earnings_manager.get_teacher_earnings(str(user_id))
    
    if not earnings:
        await query.edit_message_text(
            "📊 *Daromadlar tarixi*\n\n"
            "Hozircha daromadlar yo'q.\n\n"
            "Pullik testlar yaratib, talabalar ishlashini kuting.",
            parse_mode='Markdown'
        )
        return
    
    message = "📊 *Daromadlar tarixi*\n\n"
    
    # Show last 10 earnings
    for i, earning in enumerate(earnings[:10], 1):
        date = earning['created_at'][:10]
        message += (
            f"{i}. 📅 {date}\n"
            f"   💰 {earning['teacher_share']} ⭐ (Jami: {earning['total_amount']} ⭐)\n"
            f"   📝 Test ID: `{earning['test_id']}`\n\n"
        )
    
    if len(earnings) > 10:
        message += f"\n... va yana {len(earnings) - 10} ta to'lov"
    
    stats = earnings_manager.get_earnings_stats(str(user_id))
    message += (
        f"\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 *Umumiy statistika:*\n"
        f"  • Jami daromad: {stats['total_earnings']} ⭐\n"
        f"  • To'lovlar soni: {stats['total_transactions']} ta\n"
        f"  • O'rtacha daromad: {stats['average_earning']:.1f} ⭐"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="back_to_balance")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def request_withdrawal(query, context: ContextTypes.DEFAULT_TYPE):
    """Pul yechib olish so'rovi boshlash"""
    user_id = query.from_user.id
    balance = earnings_manager.get_teacher_balance(str(user_id))
    
    if balance['available'] < 10:
        await query.answer(
            f"❌ Yetarli mablag' yo'q! Minimal: 10 ⭐, Mavjud: {balance['available']} ⭐",
            show_alert=True
        )
        return
    
    context.user_data['withdrawal_step'] = 'amount'
    
    await query.edit_message_text(
        f"💸 *Pul yechib olish*\n\n"
        f"💰 Mavjud balans: {balance['available']} ⭐\n\n"
        f"Yechib olmoqchi bo'lgan miqdorni kiriting:\n"
        f"(10 dan {balance['available']} gacha)\n\n"
        f"Bekor qilish uchun /cancel",
        parse_mode='Markdown'
    )


async def handle_withdrawal_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal-related callback queries"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "withdraw_money":
        await request_withdrawal(query, context)
    
    elif query.data == "earnings_history":
        await show_earnings_history(query, context)
    
    elif query.data == "withdrawal_ton":
        context.user_data['withdrawal_method'] = 'TON'
        context.user_data['withdrawal_step'] = 'wallet'
        
        amount = context.user_data.get('withdrawal_amount', 0)
        
        await query.edit_message_text(
            f"💎 *TON hamyon orqali yechib olish*\n\n"
            f"💰 Miqdor: {amount} ⭐\n\n"
            f"TON hamyon manzilingizni kiriting:\n"
            f"(Masalan: UQD... yoki EQD...)\n\n"
            f"Bekor qilish uchun /cancel",
            parse_mode='Markdown'
        )
    
    elif query.data == "withdrawal_bank":
        context.user_data['withdrawal_method'] = 'Bank'
        context.user_data['withdrawal_step'] = 'wallet'
        
        amount = context.user_data.get('withdrawal_amount', 0)
        
        await query.edit_message_text(
            f"🏦 *Bank orqali yechib olish*\n\n"
            f"💰 Miqdor: {amount} ⭐\n\n"
            f"Karta raqamingizni kiriting:\n"
            f"(16 raqamli karta raqami)\n\n"
            f"Bekor qilish uchun /cancel",
            parse_mode='Markdown'
        )
    
    elif query.data == "withdrawal_cancel":
        context.user_data['withdrawal_step'] = None
        context.user_data['withdrawal_amount'] = None
        context.user_data['withdrawal_method'] = None
        
        await query.edit_message_text(
            "❌ Pul yechib olish bekor qilindi.",
            parse_mode='Markdown'
        )
    
    elif query.data == "back_to_balance":
        # Show balance again
        user_id = query.from_user.id
        balance = earnings_manager.get_teacher_balance(str(user_id))
        earnings = earnings_manager.get_teacher_earnings(str(user_id))
        
        message = (
            f"💰 *Sizning balansing*\n\n"
            f"📊 Umumiy daromad: {balance['total_earned']} ⭐\n"
            f"💵 Mavjud: {balance['available']} ⭐\n"
            f"⏳ Kutilmoqda: {balance['pending']} ⭐\n"
            f"✅ Yechib olingan: {balance['withdrawn']} ⭐\n\n"
            f"📝 Jami to'lovlar: {len(earnings)} ta"
        )
        
        keyboard = []
        
        if balance['available'] >= 10:
            keyboard.append([
                InlineKeyboardButton("💸 Pul yechib olish", callback_data="withdraw_money")
            ])
        
        keyboard.append([
            InlineKeyboardButton("📜 Daromadlar tarixi", callback_data="earnings_history")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_withdrawal_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle withdrawal amount and method input"""
    user_id = update.effective_user.id
    withdrawal_step = context.user_data.get('withdrawal_step')
    
    if withdrawal_step == 'amount':
        try:
            amount = int(text)
            balance = earnings_manager.get_teacher_balance(str(user_id))
            
            if amount < 10:
                await update.message.reply_text("❌ Minimal miqdor 10 ⭐")
                return True
            
            if amount > balance['available']:
                await update.message.reply_text(
                    f"❌ Yetarli mablag' yo'q!\n"
                    f"Mavjud: {balance['available']} ⭐"
                )
                return True
            
            context.user_data['withdrawal_amount'] = amount
            context.user_data['withdrawal_step'] = 'method'
            
            keyboard = [
                [InlineKeyboardButton("💎 TON hamyon", callback_data="withdrawal_ton")],
                [InlineKeyboardButton("🏦 Bank", callback_data="withdrawal_bank")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="withdrawal_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"💸 Yechib olish miqdori: {amount} ⭐\n\n"
                "To'lov usulini tanlang:",
                reply_markup=reply_markup
            )
            return True
            
        except ValueError:
            await update.message.reply_text("❌ Iltimos, raqam kiriting!")
            return True
    
    elif withdrawal_step == 'wallet':
        wallet_address = text.strip()
        amount = context.user_data.get('withdrawal_amount', 0)
        method = context.user_data.get('withdrawal_method', 'TON')
        
        # Create withdrawal request
        result = earnings_manager.create_withdrawal_request(
            teacher_id=str(user_id),
            amount=amount,
            method=method,
            wallet_address=wallet_address
        )
        
        if 'error' in result:
            await update.message.reply_text(f"❌ {result['error']}")
            return True
        
        await update.message.reply_text(
            f"✅ *Pul yechib olish so'rovi yuborildi!*\n\n"
            f"💰 Miqdor: {amount} ⭐\n"
            f"💳 Usul: {method}\n"
            f"📍 Manzil: `{wallet_address}`\n\n"
            f"📝 So'rov ID: #{result['id']}\n\n"
            f"Admin tekshirgandan keyin sizga xabar beriladi.",
            parse_mode='Markdown'
        )
        
        # Clear withdrawal data
        context.user_data['withdrawal_step'] = None
        context.user_data['withdrawal_amount'] = None
        context.user_data['withdrawal_method'] = None
        
        return True
    
    return False
