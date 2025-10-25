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


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin panel with inline keyboard (admin only)"""
    user_id = update.effective_user.id
    
    if not payment_manager.is_admin(user_id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
        return
    
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
            InlineKeyboardButton("💵 Narxni o'zgartirish", callback_data="admin_change_price")
        ],
        [
            InlineKeyboardButton("📋 Batafsil hisobot", callback_data="admin_detailed_report"),
            InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💼 *Admin Panel*\n\n"
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
    
    elif query.data == "admin_detailed_report":
        await show_detailed_report(query, context)
    
    elif query.data == "admin_settings":
        await show_admin_settings(query, context)
    
    elif query.data == "admin_back":
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
                InlineKeyboardButton("💵 Narxni o'zgartirish", callback_data="admin_change_price")
            ],
            [
                InlineKeyboardButton("📋 Batafsil hisobot", callback_data="admin_detailed_report"),
                InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👨‍💼 *Admin Panel*\n\n"
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
    
    message = (
        f"⚙️ *Sozlamalar*\n\n"
        f"💵 Tahlil narxi: {config['analysis_price_stars']} ⭐ Stars\n"
        f"💱 Valyuta: {config['currency']}\n\n"
        f"👨‍💼 *Admin User ID:*\n"
        f"  • {admin_id}\n"
        f"\n💡 Admin ID ni `.env` faylidan o'zgartiring"
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
