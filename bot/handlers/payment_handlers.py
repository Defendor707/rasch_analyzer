import logging
from telegram import Update, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils.payment_manager import PaymentManager
from bot.utils.bonus_manager import BonusManager

logger = logging.getLogger(__name__)
payment_manager = PaymentManager()
bonus_manager = BonusManager()


async def create_payment_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 file_name: str):
    """Create and send payment invoice for file analysis"""
    user_id = update.effective_user.id
    config = payment_manager.get_config()
    price_stars = config['analysis_price_stars']
    
    # Bonus chegirmasini hisoblash
    discount, final_price = bonus_manager.calculate_discount(user_id, price_stars)
    user_bonus = bonus_manager.get_user_bonus(user_id)
    
    title = "📊 Rasch tahlili"
    
    bonus_text = ""
    if discount > 0:
        bonus_text = f"\n\n🎁 Bonus chegirma: -{discount} ⭐\n💰 Asl narx: {price_stars} ⭐"
    
    description = f"Fayl tahlili: {file_name}{bonus_text}\n\nTo'lovdan keyin PDF hisobot yuboriladi."
    payload = f"analysis_{user_id}_{file_name}_{discount}"
    
    prices = [LabeledPrice("Rasch tahlili", final_price)]
    
    # Bonus ma'lumotini saqlash
    context.user_data['bonus_discount_used'] = discount
    context.user_data['original_price'] = price_stars
    
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
    
    # Bonus ishlatilganini tekshirish
    bonus_used = context.user_data.get('bonus_discount_used', 0)
    if bonus_used > 0:
        bonus_manager.use_bonus(user_id, bonus_used)
    
    payment_id = payment_manager.record_payment(
        user_id=user_id,
        amount_stars=payment_info.total_amount,
        telegram_payment_charge_id=payment_info.telegram_payment_charge_id,
        file_name=file_name
    )
    
    logger.info(f"To'lov muvaffaqiyatli: User {user_id}, File: {file_name}, Stars: {payment_info.total_amount}, Bonus: {bonus_used}")
    
    bonus_text = f"\n🎁 Bonus ishlatildi: {bonus_used} ⭐" if bonus_used > 0 else ""
    
    await update.message.reply_text(
        f"✅ To'lov muvaffaqiyatli qabul qilindi!\n\n"
        f"💰 To'langan: {payment_info.total_amount} ⭐ Stars{bonus_text}\n"
        f"📄 Fayl: {file_name}\n\n"
        f"⏳ Tahlil jarayoni boshlanmoqda..."
    )
    
    context.user_data['payment_completed'] = True
    context.user_data['paid_file_name'] = file_name
    
    # Start analysis after successful payment
    from bot.handlers.message_handlers import perform_analysis_after_payment
    await perform_analysis_after_payment(update.message, context)


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


async def show_bot_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot's Telegram Stars balance and transaction history (admin only)"""
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
        return
    
    try:
        # Get star transactions from Telegram API
        transactions = await context.bot.get_star_transactions(limit=100)
        
        # Calculate total balance from transactions
        total_received = 0
        total_withdrawn = 0
        
        for tx in transactions.transactions:
            if tx.amount > 0:
                total_received += tx.amount
            else:
                total_withdrawn += abs(tx.amount)
        
        current_balance = total_received - total_withdrawn
        
        # Get local payment stats
        stats = payment_manager.get_payment_stats()
        
        message = (
            f"💰 *Bot Stars Balansi*\n\n"
            f"⭐ *Telegram API:*\n"
            f"  • Hozirgi balans: {current_balance} Stars\n"
            f"  • Jami qabul qilingan: {total_received} Stars\n"
            f"  • Yechib olingan: {total_withdrawn} Stars\n\n"
            f"📊 *Lokal statistika:*\n"
            f"  • Jami to'lovlar: {stats['total_payments']} ta\n"
            f"  • Jami Stars: {stats['total_stars']} ⭐\n"
            f"  • To'lov qilganlar: {stats['unique_users']} ta\n\n"
        )
        
        if current_balance >= 1000:
            message += "✅ Yechib olish mumkin (min. 1000 Stars)\n"
            message += "💡 Fragment orqali TON hamyoningizga o'tkazing"
        else:
            remaining = 1000 - current_balance
            message += f"⏳ Yechib olish uchun yana {remaining} Stars kerak"
        
        # Show recent transactions
        if transactions.transactions:
            message += "\n\n📜 *So'nggi tranzaksiyalar:*\n"
            for i, tx in enumerate(transactions.transactions[:5], 1):
                from datetime import datetime
                date = datetime.fromtimestamp(tx.date).strftime('%d.%m.%Y %H:%M')
                amount_str = f"+{tx.amount}" if tx.amount > 0 else str(tx.amount)
                message += f"{i}. {amount_str} ⭐ - {date}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Balansni olishda xatolik: {e}")
        
        # Fallback to local stats only
        stats = payment_manager.get_payment_stats()
        
        message = (
            f"💰 *Bot Statistikasi*\n\n"
            f"📊 *Lokal ma'lumotlar:*\n"
            f"  • Jami to'lovlar: {stats['total_payments']} ta\n"
            f"  • Jami Stars: {stats['total_stars']} ⭐\n"
            f"  • To'lov qilganlar: {stats['unique_users']} ta\n\n"
            f"⚠️ *Telegram API orqali balansni ololmadik.*\n\n"
            f"💡 Balansni BotFatherdan ko'ring:\n"
            f"   @BotFather → Botingiz → Edit → Balance\n\n"
            f"📌 *Eslatma:* Balans birinchi to'lovdan 1-2 soat keyin ko'rinadi."
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin panel with inline keyboard (admin only)"""
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
        return
    
    # Check payment status for dynamic button text
    config = payment_manager.get_config()
    payment_enabled = config.get('payment_enabled', True)
    payment_toggle_text = "🔴 Tekin qilish" if payment_enabled else "🟢 Pullik qilish"
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Foydalanuvchilar", callback_data="admin_user_stats"),
            InlineKeyboardButton("💰 To'lovlar", callback_data="admin_payment_stats")
        ],
        [
            InlineKeyboardButton("📈 Xizmatlar", callback_data="admin_service_stats"),
            InlineKeyboardButton("🤖 Bot statistikasi", callback_data="admin_bot_stats")
        ],
        [
            InlineKeyboardButton("💵 Narxni o'zgartirish", callback_data="admin_change_price"),
            InlineKeyboardButton(payment_toggle_text, callback_data="admin_toggle_payment")
        ],
        [
            InlineKeyboardButton("📋 Batafsil hisobot", callback_data="admin_detailed_report"),
            InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_icon = "🟢 Tekin" if not payment_enabled else "💰 Pullik"
    
    await update.message.reply_text(
        f"👨‍💼 *Admin Panel*\n\n"
        f"Hozirgi rejim: {status_icon}\n\n"
        "Kerakli bo'limni tanlang:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        await query.edit_message_text("❌ Sizda admin huquqlari yo'q!")
        return
    
    if query.data == "admin_user_stats":
        await show_user_statistics(query, context)
    
    elif query.data == "admin_payment_stats":
        await show_payment_statistics(query, context)
    
    elif query.data == "admin_service_stats":
        await show_service_statistics(query, context)
    
    elif query.data == "admin_bot_stats":
        await show_bot_statistics(query, context)
    
    elif query.data == "admin_change_price":
        await query.edit_message_text(
            "💵 *Narxni o'zgartirish*\n\n"
            "Yangi narxni quyidagi formatda yuboring:\n"
            "`narx:150`\n\n"
            "Bu yerda 150 - yangi narx Stars da.",
            parse_mode='Markdown'
        )
        context.user_data['admin_waiting_price'] = True
    
    elif query.data == "admin_toggle_payment":
        config = payment_manager.get_config()
        current_status = config.get('payment_enabled', True)
        new_status = not current_status
        
        payment_manager.toggle_payment_mode(new_status)
        
        status_text = "pullik" if new_status else "tekin"
        status_icon = "💰" if new_status else "🟢"
        
        await query.answer(f"{status_icon} Xizmat endi {status_text}!", show_alert=True)
        
        # Update keyboard
        payment_toggle_text = "🔴 Tekin qilish" if new_status else "🟢 Pullik qilish"
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Foydalanuvchilar", callback_data="admin_user_stats"),
                InlineKeyboardButton("💰 To'lovlar", callback_data="admin_payment_stats")
            ],
            [
                InlineKeyboardButton("📈 Xizmatlar", callback_data="admin_service_stats"),
                InlineKeyboardButton("🤖 Bot statistikasi", callback_data="admin_bot_stats")
            ],
            [
                InlineKeyboardButton("💵 Narxni o'zgartirish", callback_data="admin_change_price"),
                InlineKeyboardButton(payment_toggle_text, callback_data="admin_toggle_payment")
            ],
            [
                InlineKeyboardButton("📋 Batafsil hisobot", callback_data="admin_detailed_report"),
                InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_display = "🟢 Tekin" if not new_status else "💰 Pullik"
        
        await query.edit_message_text(
            f"👨‍💼 *Admin Panel*\n\n"
            f"Hozirgi rejim: {status_display}\n\n"
            "Kerakli bo'limni tanlang:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "admin_detailed_report":
        await show_detailed_report(query, context)
    
    elif query.data == "admin_settings":
        await show_admin_settings(query, context)
    
    elif query.data == "admin_back":
        # Check payment status for dynamic button
        config = payment_manager.get_config()
        payment_enabled = config.get('payment_enabled', True)
        payment_toggle_text = "🔴 Tekin qilish" if payment_enabled else "🟢 Pullik qilish"
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Foydalanuvchilar", callback_data="admin_user_stats"),
                InlineKeyboardButton("💰 To'lovlar", callback_data="admin_payment_stats")
            ],
            [
                InlineKeyboardButton("📈 Xizmatlar", callback_data="admin_service_stats"),
                InlineKeyboardButton("🤖 Bot statistikasi", callback_data="admin_bot_stats")
            ],
            [
                InlineKeyboardButton("💵 Narxni o'zgartirish", callback_data="admin_change_price"),
                InlineKeyboardButton(payment_toggle_text, callback_data="admin_toggle_payment")
            ],
            [
                InlineKeyboardButton("📋 Batafsil hisobot", callback_data="admin_detailed_report"),
                InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_icon = "🟢 Tekin" if not payment_enabled else "💰 Pullik"
        
        await query.edit_message_text(
            f"👨‍💼 *Admin Panel*\n\n"
            f"Hozirgi rejim: {status_icon}\n\n"
            "Kerakli bo'limni tanlang:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def show_user_statistics(query, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    from bot.utils.user_data import UserDataManager
    
    user_manager = UserDataManager()
    
    try:
        import json
        with open('data/user_profiles.json', 'r', encoding='utf-8') as f:
            all_users = json.load(f)
        
        total_users = len(all_users)
        users_with_subject = sum(1 for u in all_users.values() if u.get('subject'))
        
        subjects = {}
        for user_data in all_users.values():
            subject = user_data.get('subject')
            if subject:
                subjects[subject] = subjects.get(subject, 0) + 1
        
        message = (
            f"📊 *Foydalanuvchilar statistikasi*\n\n"
            f"👥 Jami foydalanuvchilar: {total_users} ta\n"
            f"📚 Fan tanlagan: {users_with_subject} ta\n\n"
            f"*Fanlar bo'yicha:*\n"
        )
        
        for subject, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True):
            message += f"  • {subject}: {count} ta\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    except Exception as e:
        await query.edit_message_text(f"❌ Xatolik: {str(e)}")


async def show_payment_statistics(query, context: ContextTypes.DEFAULT_TYPE):
    """Show payment statistics"""
    stats = payment_manager.get_payment_stats()
    config = payment_manager.get_config()
    
    message = (
        f"💰 *To'lovlar statistikasi*\n\n"
        f"💳 Jami to'lovlar: {stats['total_payments']} ta\n"
        f"⭐ Jami Stars: {stats['total_stars']}\n"
        f"👥 To'lov qilganlar: {stats['unique_users']} ta\n\n"
        f"💵 Joriy narx: {config['analysis_price_stars']} ⭐ Stars\n"
    )
    
    if stats['latest_payment']:
        latest = stats['latest_payment']
        message += f"\n🕐 So'nggi to'lov:\n"
        message += f"   📅 {latest['timestamp'][:16]}\n"
        message += f"   👤 User ID: {latest['user_id']}\n"
        message += f"   💰 {latest['amount_stars']} Stars\n"
    
    if stats['total_payments'] > 0:
        avg_stars = stats['total_stars'] / stats['total_payments']
        message += f"\n📊 O'rtacha to'lov: {avg_stars:.1f} Stars\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def show_service_statistics(query, context: ContextTypes.DEFAULT_TYPE):
    """Show most used services statistics"""
    try:
        payments = payment_manager.get_all_payments()
        
        total_analyses = len(payments)
        
        file_types = {}
        for payment in payments:
            file_name = payment.get('file_name', '')
            if file_name:
                ext = file_name.split('.')[-1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1
        
        message = (
            f"📈 *Xizmatlar statistikasi*\n\n"
            f"📊 Jami tahlillar: {total_analyses} ta\n\n"
        )
        
        if file_types:
            message += "*Fayl turlari:*\n"
            for ftype, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_analyses) * 100
                message += f"  • .{ftype}: {count} ta ({percentage:.1f}%)\n"
        
        message += (
            f"\n*Eng ko'p ishlatiladigan xizmat:*\n"
            f"  ⭐ Rasch tahlili: {total_analyses} marta\n"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    except Exception as e:
        await query.edit_message_text(f"❌ Xatolik: {str(e)}")


async def show_bot_statistics(query, context: ContextTypes.DEFAULT_TYPE):
    """Show overall bot statistics"""
    try:
        import json
        from datetime import datetime, timedelta
        
        with open('data/user_profiles.json', 'r', encoding='utf-8') as f:
            all_users = json.load(f)
        
        total_users = len(all_users)
        
        payments = payment_manager.get_all_payments()
        total_revenue = sum(p['amount_stars'] for p in payments)
        
        with open('data/students.json', 'r', encoding='utf-8') as f:
            students_data = json.load(f)
        total_students = sum(len(students) for students in students_data.values())
        
        with open('data/tests.json', 'r', encoding='utf-8') as f:
            tests_data = json.load(f)
        total_tests = len(tests_data)
        active_tests = sum(1 for t in tests_data.values() if t.get('is_active'))
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        recent_payments = [p for p in payments 
                          if datetime.fromisoformat(p['timestamp']).date() >= week_ago]
        
        message = (
            f"🤖 *Bot statistikasi*\n\n"
            f"👥 Jami foydalanuvchilar: {total_users} ta\n"
            f"👨‍🎓 Jami o'quvchilar: {total_students} ta\n"
            f"📝 Jami testlar: {total_tests} ta\n"
            f"✅ Faol testlar: {active_tests} ta\n\n"
            f"💰 *Moliyaviy:*\n"
            f"  ⭐ Jami daromad: {total_revenue} Stars\n"
            f"  💳 Jami to'lovlar: {len(payments)} ta\n"
            f"  📅 Oxirgi 7 kun: {len(recent_payments)} ta to'lov\n"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    except Exception as e:
        await query.edit_message_text(f"❌ Xatolik: {str(e)}")


async def show_detailed_report(query, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed comprehensive report"""
    try:
        import json
        from datetime import datetime
        
        with open('data/user_profiles.json', 'r', encoding='utf-8') as f:
            all_users = json.load(f)
        
        payments = payment_manager.get_all_payments()
        config = payment_manager.get_config()
        
        message = (
            f"📋 *Batafsil hisobot*\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"═══════════════════════\n\n"
            f"👥 FOYDALANUVCHILAR:\n"
            f"  • Jami: {len(all_users)} ta\n\n"
            f"💰 TO'LOVLAR:\n"
            f"  • Jami: {len(payments)} ta\n"
            f"  • Stars: {sum(p['amount_stars'] for p in payments)}\n"
            f"  • O'rtacha: {sum(p['amount_stars'] for p in payments) / len(payments) if payments else 0:.1f} Stars\n\n"
            f"💵 SOZLAMALAR:\n"
            f"  • Joriy narx: {config['analysis_price_stars']} Stars\n"
            f"  • Adminlar: {len(config['admin_ids'])} ta\n\n"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    except Exception as e:
        await query.edit_message_text(f"❌ Xatolik: {str(e)}")


async def show_admin_settings(query, context: ContextTypes.DEFAULT_TYPE):
    """Show admin settings"""
    import os
    config = payment_manager.get_config()
    
    admin_id = os.getenv('ADMIN_TELEGRAM_ID', 'Sozlanmagan')
    payment_enabled = config.get('payment_enabled', True)
    payment_status = "💰 Pullik" if payment_enabled else "🟢 Tekin"
    
    message = (
        f"⚙️ *Sozlamalar*\n\n"
        f"🎯 *Xizmat rejimi:* {payment_status}\n"
        f"💵 Tahlil narxi: {config['analysis_price_stars']} ⭐ Stars\n"
        f"💱 Valyuta: {config['currency']}\n\n"
        f"👨‍💼 *Admin User ID:*\n"
        f"  • {admin_id}\n"
        f"\n💡 Sozlamalarni admin paneldan o'zgartiring"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Ortga", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle admin text inputs for price and admin ID"""
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        return False
    
    if context.user_data.get('admin_waiting_price'):
        if text.startswith('narx:'):
            try:
                new_price = int(text.split(':')[1].strip())
                if new_price <= 0:
                    await update.message.reply_text("❌ Narx musbat bo'lishi kerak!")
                    return True
                
                payment_manager.update_price(new_price)
                await update.message.reply_text(
                    f"✅ *Narx yangilandi!*\n\n"
                    f"Yangi narx: {new_price} ⭐ Stars",
                    parse_mode='Markdown'
                )
                context.user_data['admin_waiting_price'] = False
                return True
            except (ValueError, IndexError):
                await update.message.reply_text("❌ Noto'g'ri format! Masalan: `narx:150`", parse_mode='Markdown')
                return True
    
    return False
