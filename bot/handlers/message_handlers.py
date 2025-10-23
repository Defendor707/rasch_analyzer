import os
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils.rasch_analysis import RaschAnalyzer
from bot.utils.pdf_generator import PDFReportGenerator
from bot.utils.user_data import UserDataManager
from bot.utils.student_data import StudentDataManager
from bot.utils.subject_sections import get_sections, has_sections
from bot.utils.data_cleaner import DataCleaner
import logging

logger = logging.getLogger(__name__)

# Initialize user data manager
user_data_manager = UserDataManager()
student_data_manager = StudentDataManager()

# Conversation states
WAITING_FOR_FULL_NAME = 1
WAITING_FOR_BIO = 2
WAITING_FOR_SUBJECT = 3
WAITING_FOR_STUDENT_NAME = 4
WAITING_FOR_STUDENT_TELEGRAM = 5
WAITING_FOR_PARENT_TELEGRAM = 6
WAITING_FOR_SECTION_QUESTIONS = 7


def get_main_keyboard():
    """Create main reply keyboard with 4 buttons"""
    keyboard = [
        [KeyboardButton("👤 Profil"), KeyboardButton("⚙️ Sozlamalar")],
        [KeyboardButton("👥 O'quvchilar"), KeyboardButton("ℹ️ Boshqa")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued"""
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)
    
    # Disable file analyzer mode when starting
    user_data_manager.update_user_field(user_id, 'file_analyzer_mode', False)

    full_name = user_data.get('full_name')
    if not full_name:
        full_name = update.effective_user.first_name or "foydalanuvchi"

    welcome_message = (
        f"👋 Assalomu alaykum, {full_name}!\n\n"
        "🎓 Rasch analiyzer botga xush kelibsiz!\n\n"
        "📝 Matritsani yuboring yoki /namuna buyrug'i bilan namuna tahlilni ko'ring\n\n"
        "/help commandasini yuborib foydalanish yo'riqnomasi bilan tanishing."
    )

    file_info_message = (
        "📊 Excel (.xls, .xlsx, .csv) faylni yuborishingiz mumkin!"
    )

    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())
    await update.message.reply_text(file_info_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when the command /help is issued"""
    help_message = (
        "*📖 Yordam*\n\n"
        "*Fayl talablari:*\n"
        "• Format: CSV (.csv) yoki Excel (.xlsx, .xls)\n"
        "• Qatorlar: Har bir qator - bitta ishtirokchi\n"
        "• Ustunlar: Har bir ustun - bitta savol/item\n"
        "• Qiymatlar: Faqat 0 va 1 (dikotomik ma'lumotlar)\n\n"
        "*Misol ma'lumotlar strukturasi:*\n"
        "```\n"
        "Item1, Item2, Item3, Item4\n"
        "1,     0,     1,     1\n"
        "0,     0,     0,     1\n"
        "1,     1,     1,     1\n"
        "```\n\n"
        "*Natijalar:*\n"
        "PDF hisobotda quyidagilar bo'ladi:\n"
        "✓ Item difficulty parametrlari\n"
        "✓ Person ability ko'rsatkichlari\n"
        "✓ Reliability (ishonchlilik)\n"
        "✓ Deskriptiv statistika\n\n"
        "Savol bo'lsa, fayl yuboring va tahlil boshlaylik!"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def sample_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and analyze sample data with 50 persons and 55 items"""
    user_id = update.effective_user.id

    await update.message.reply_text(
        "🔬 Namunaviy ma'lumotlar yaratilmoqda...\n"
        "📊 50 talabgor va 55 savol"
    )

    try:
        import numpy as np

        # Generate sample data: 50 persons × 55 items
        np.random.seed(42)  # For reproducibility
        n_persons = 50
        n_items = 55

        # Generate abilities for persons (mean=0, sd=1)
        person_abilities = np.random.normal(0, 1, n_persons)

        # Generate item difficulties (mean=0, sd=1.2)
        item_difficulties = np.random.normal(0, 1.2, n_items)

        # Generate responses using Rasch model
        sample_data = np.zeros((n_persons, n_items))
        for i in range(n_persons):
            for j in range(n_items):
                # Rasch probability
                prob = 1 / (1 + np.exp(-(person_abilities[i] - item_difficulties[j])))
                # Generate response
                sample_data[i, j] = 1 if np.random.random() < prob else 0

        # Create DataFrame with item names
        item_names = [f"Savol_{i+1}" for i in range(n_items)]
        data = pd.DataFrame(sample_data, columns=item_names)

        await update.message.reply_text("⏳ Tahlil boshlanmoqda...")

        # Perform Rasch analysis
        analyzer = RaschAnalyzer()
        results = analyzer.fit(data.astype(int))

        pdf_generator = PDFReportGenerator()

        # Generate general statistics report
        general_pdf_path = pdf_generator.generate_report(
            results,
            filename=f"namuna_umumiy_{user_id}"
        )

        # Get section questions if configured
        user_data = user_data_manager.get_user_data(user_id)
        section_questions = user_data.get('section_questions')
        section_results_enabled = user_data.get('section_results_enabled', False)

        # Generate person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename=f"namuna_talabgorlar_{user_id}",
            section_questions=section_questions if section_results_enabled else None
        )

        await update.message.reply_text(
            f"✅ *Namunaviy tahlil tugallandi!*\n\n"
            f"📊 Talabgorlar: {results['n_persons']}\n"
            f"📝 Savollar: {results['n_items']}\n"
            f"📈 Reliability: {results['reliability']:.3f}\n\n"
            f"PDF hisobotlar yuborilmoqda...",
            parse_mode='Markdown'
        )

        # Send general statistics PDF
        if general_pdf_path and os.path.exists(general_pdf_path):
            with open(general_pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(general_pdf_path),
                    caption="📊 Namunaviy tahlil - Umumiy statistika"
                )

        # Send person results PDF
        with open(person_pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=os.path.basename(person_pdf_path),
                caption="👥 Namunaviy tahlil - Talabgorlar natijalari"
            )

        # Generate and send section results if enabled and configured
        if section_results_enabled and section_questions:
            section_pdf_path = pdf_generator.generate_section_results_report(
                results,
                filename=f"namuna_bulimlar_{user_id}",
                section_questions=section_questions
            )

            with open(section_pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(section_pdf_path),
                    caption="📋 Namunaviy tahlil - Bo'limlar bo'yicha natijalar"
                )

        logger.info(f"Sample analysis completed for user {user_id}")

    except Exception as e:
        import traceback
        logger.error(f"Error in sample analysis for user {user_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        await update.message.reply_text(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos, qayta urinib ko'ring."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded document files"""
    document = update.message.document
    user_id = update.effective_user.id

    file_extension = os.path.splitext(document.file_name)[1].lower()
    if file_extension not in ['.csv', '.xlsx', '.xls']:
        await update.message.reply_text(
            "❌ Noto'g'ri fayl formati!\n\n"
            "Iltimos, CSV (.csv) yoki Excel (.xlsx, .xls) formatdagi fayl yuboring."
        )
        return

    # Check if user is in File Analyzer mode
    user_data = user_data_manager.get_user_data(user_id)
    file_analyzer_mode = user_data.get('file_analyzer_mode', False)

    if file_analyzer_mode:
        # FILE ANALYZER MODE: Clean or Standardize the file
        operation = user_data.get('file_analyzer_operation', 'full_clean')
        
        if operation == 'standardize':
            await update.message.reply_text("📝 File Analyzer rejimi: Fayl standartlashtirilmoqda...")
        else:
            await update.message.reply_text("🧹 File Analyzer rejimi: Fayl tozalanmoqda...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            upload_dir = "data/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"{user_id}_{document.file_name}")
            await file.download_to_drive(file_path)

            # Read file
            if file_extension == '.csv':
                try:
                    data = pd.read_csv(file_path)
                except Exception:
                    data = pd.read_csv(file_path, encoding='latin-1')
            else:
                data = pd.read_excel(file_path)

            cleaner = DataCleaner()
            
            # Perform the selected operation
            if operation == 'standardize':
                # Faqat standartlashtirish
                processed_data, metadata = cleaner.standardize_data(data)
                report = cleaner.get_standardization_report(metadata)
                output_prefix = "standardized"
                success_message = "✅ Standartlashtirilgan fayl tayyor!\n\n" \
                                "Ustun nomlari Savol_1, Savol_2, ... formatiga keltirildi.\n" \
                                "Endi uni tahlil qilish uchun qayta yuboring yoki /start orqali chiqing."
            else:
                # To'liq tozalash
                processed_data, metadata = cleaner.clean_data(data)
                report = cleaner.get_cleaning_report(metadata)
                output_prefix = "cleaned"
                success_message = "✅ Tozalangan fayl tayyor!\n\n" \
                                "Bu faylda faqat 0/1 matritsasi mavjud.\n" \
                                "Endi uni tahlil qilish uchun qayta yuboring yoki /start orqali chiqing."
            
            # Send report
            await update.message.reply_text(report)
            
            # Save processed file
            processed_file_path = os.path.join(upload_dir, f"{output_prefix}_{user_id}_{document.file_name}")
            if file_extension == '.csv':
                processed_data.to_csv(processed_file_path, index=False)
            else:
                processed_data.to_excel(processed_file_path, index=False)
            
            # Send processed file back to user
            with open(processed_file_path, 'rb') as processed_file:
                await update.message.reply_document(
                    document=processed_file,
                    filename=f"{output_prefix}_{document.file_name}",
                    caption=success_message
                )
            
            # Cleanup
            os.remove(file_path)
            os.remove(processed_file_path)
            
            logger.info(f"File {operation} completed successfully for user {user_id}")
            return
            
        except Exception as e:
            logger.error(f"Error processing file for user {user_id}: {str(e)}")
            await update.message.reply_text(
                f"❌ Faylni qayta ishlashda xatolik: {str(e)}\n\n"
                "Iltimos, faylingizni tekshiring va qayta urinib ko'ring."
            )
            return

    # NORMAL MODE: Analyze the file
    await update.message.reply_text("⏳ Fayl qabul qilindi. Tahlil boshlanmoqda...")

    try:
        file = await context.bot.get_file(document.file_id)

        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, f"{user_id}_{document.file_name}")
        await file.download_to_drive(file_path)

        if file_extension == '.csv':
            try:
                data = pd.read_csv(file_path)
            except Exception:
                data = pd.read_csv(file_path, encoding='latin-1')
        else:
            data = pd.read_excel(file_path)

        # In normal mode, use data as-is (no auto-cleaning)
        numeric_data = data
        
        # Validate that data is numeric and binary
        if not all(numeric_data.apply(pd.to_numeric, errors='coerce').notna().all()):
            await update.message.reply_text(
                "⚠️ Ogohlantirish: Faylda raqamiy bo'lmagan ma'lumotlar bor.\n"
                "Ular 0 ga aylantiriladi."
            )
            numeric_data = numeric_data.apply(pd.to_numeric, errors='coerce').fillna(0)
        
        # Additional validation
        if not all(numeric_data.isin([0, 1]).all()):
            await update.message.reply_text(
                "⚠️ Ogohlantirish: Ba'zi qiymatlar 0 va 1 dan farq qiladi.\n"
                "Ular eng yaqin qiymatga yaxlitlanadi."
            )
            # Round to nearest integer and clip to 0-1
            numeric_data = numeric_data.round().clip(0, 1)

        # Convert to integer type for girth library
        numeric_data = numeric_data.astype(int)

        analyzer = RaschAnalyzer()
        results = analyzer.fit(numeric_data)

        summary_text = analyzer.get_summary(results)

        pdf_generator = PDFReportGenerator()

        # Generate general statistics report
        general_pdf_path = pdf_generator.generate_report(
            results,
            filename=f"umumiy_statistika_{user_id}"
        )

        # Get section questions if configured
        user_data = user_data_manager.get_user_data(user_id)
        section_questions = user_data.get('section_questions')
        selected_subject = user_data.get('subject', '')

        # Check if section results is enabled and section_questions are configured
        section_results_enabled = user_data.get('section_results_enabled', False)

        if section_results_enabled and not section_questions and selected_subject and has_sections(selected_subject):
            # Store results temporarily
            context.user_data['pending_results'] = results
            context.user_data['pending_general_pdf'] = general_pdf_path

            # Start section configuration
            sections = get_sections(selected_subject)
            context.user_data['configuring_sections'] = True
            context.user_data['current_subject'] = selected_subject
            context.user_data['sections_list'] = sections
            context.user_data['current_section_index'] = 0
            context.user_data['section_questions'] = {}

            await update.message.reply_text(
                f"📋 *{selected_subject}* fani uchun bo'limlar bo'yicha savol raqamlarini kiritish:\n\n"
                f"Jami {len(sections)} ta bo'lim mavjud.\n\n"
                f"*1-bo'lim: {sections[0]}*\n\n"
                f"Ushbu bo'limga tegishli savol raqamlarini kiriting.\n\n"
                f"Formatlar:\n"
                f"• Bitta raqam: 5\n"
                f"• Vergul bilan ajratilgan: 1,2,3,4,5\n"
                f"• Diapazon: 1-10\n"
                f"• Aralash: 1-5,7,9,11-15\n\n"
                f"Bo'limni o'tkazib yuborish uchun 'o'tkazib' deb yozing.",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            return

        # Generate person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename=f"talabgorlar_natijalari_{user_id}",
            section_questions=section_questions if section_results_enabled else None
        )

        # Send general statistics PDF
        if general_pdf_path and os.path.exists(general_pdf_path):
            with open(general_pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(general_pdf_path),
                    caption="📊 Umumiy statistika va item parametrlari"
                )

        # Send person results PDF
        with open(person_pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=os.path.basename(person_pdf_path),
                caption="👥 Talabgorlar natijalari (Umumiy)"
            )

        # Generate and send section results if enabled and configured
        if section_results_enabled and section_questions:
            section_pdf_path = pdf_generator.generate_section_results_report(
                results,
                filename=f"bulimlar_natijalari_{user_id}",
                section_questions=section_questions
            )

            with open(section_pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(section_pdf_path),
                    caption="📋 Bo'limlar bo'yicha natijalar (T-Score)"
                )

        await update.message.reply_text(
            "✅ Barcha hisobotlar yuborildi!",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

        os.remove(file_path)

        logger.info(f"Successfully processed file for user {user_id}")

    except pd.errors.EmptyDataError:
        await update.message.reply_text(
            "❌ Fayl bo'sh yoki noto'g'ri formatda!\n"
            "Iltimos, to'g'ri ma'lumotlar bilan qayta urinib ko'ring."
        )
    except Exception as e:
        logger.error(f"Error processing file for user {user_id}: {str(e)}")
        await update.message.reply_text(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos, faylingizni tekshiring va qayta urinib ko'ring.\n"
            "Yordam kerak bo'lsa, /help buyrug'ini yuboring."
        )


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Profile button"""
    user = update.effective_user
    user_data = user_data_manager.get_user_data(user.id)

    # Display profile information
    profile_text = (
        f"👤 *Profil ma'lumotlari*\n\n"
        f"*Ism va Familiya:* {user_data.get('full_name') or 'Kiritilmagan'}\n"
        f"*Mutaxassislik:* {user_data.get('subject') or 'Kiritilmagan'}\n"
        f"*Bio:* {user_data.get('bio') or 'Kiritilmagan'}\n\n"
        f"*Telegram:* @{user.username or 'N/A'}\n"
        f"*ID:* {user.id}"
    )

    # Inline keyboard for editing
    keyboard = [
        [InlineKeyboardButton("✏️ Ism va Familiyani o'zgartirish", callback_data='edit_full_name')],
        [InlineKeyboardButton("✏️ Bio qo'shish/o'zgartirish", callback_data='edit_bio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        profile_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )



async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    if query.data == 'edit_full_name':
        context.user_data['editing'] = WAITING_FOR_FULL_NAME
        await query.message.reply_text(
            "✏️ Ism va familiyangizni kiriting (masalan: Akmal Rahimov):",
            reply_markup=get_main_keyboard()
        )

    elif query.data == 'edit_bio':
        context.user_data['editing'] = WAITING_FOR_BIO
        await query.message.reply_text(
            "✏️ O'zingiz haqida qisqacha ma'lumot kiriting:",
            reply_markup=get_main_keyboard()
        )

    # Handle section results toggle
    elif query.data == 'section_results_on':
        user_data_manager.update_user_field(user_id, 'section_results_enabled', True)
        user_data_manager.update_user_field(user_id, 'section_questions', {}) # Clear existing questions

        section_text = (
            f"📊 *Fan bo'limlari bo'yicha natijalash*\n\n"
            f"Hozirgi holat: ✅ *Yoqilgan*\n\n"
            f"Bu funksiya sizga quyidagilarni beradi:\n"
            f"• Har bir bo'lim bo'yicha natijalar\n"
            f"• Bo'limlar qiyoslash\n"
            f"• Talabgorlar yutuqlari tahlili\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✔️ Yoqilgan", callback_data='section_results_on'),
                InlineKeyboardButton("❌ O'chirish", callback_data='section_results_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            section_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("✅ Fan bo'limlari bo'yicha natijalash yoqildi!")

    elif query.data == 'section_results_off':
        user_data_manager.update_user_field(user_id, 'section_results_enabled', False)
        user_data_manager.update_user_field(user_id, 'section_questions', {}) # Clear existing questions

        section_text = (
            f"📊 *Fan bo'limlari bo'yicha natijalash*\n\n"
            f"Hozirgi holat: ❌ *O'chirilgan*\n\n"
            f"Bu funksiya sizga quyidagilarni beradi:\n"
            f"• Har bir bo'lim bo'yicha natijalar\n"
            f"• Bo'limlar qiyoslash\n"
            f"• Talabgorlar yutuqlari tahlili\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Yoqish", callback_data='section_results_on'),
                InlineKeyboardButton("✖️ O'chirilgan", callback_data='section_results_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            section_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("❌ Fan bo'limlari bo'yicha natijalash o'chirildi!")

    # Handle writing task toggle
    elif query.data == 'writing_task_on':
        user_data_manager.update_user_field(user_id, 'writing_task_enabled', True)

        writing_text = (
            f"✍️ *Yozma ish funksiyasi*\n\n"
            f"Hozirgi holat: ✅ *Yoqilgan*\n\n"
            f"Bu funksiya quyidagilarni o'z ichiga oladi:\n"
            f"• Yozma ishlarni yuklash\n"
            f"• Avtomatik baholash\n"
            f"• Tahlil va statistika\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✔️ Yoqilgan", callback_data='writing_task_on'),
                InlineKeyboardButton("❌ O'chirish", callback_data='writing_task_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            writing_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("✅ Yozma ish funksiyasi yoqildi!")

    elif query.data == 'writing_task_off':
        user_data_manager.update_user_field(user_id, 'writing_task_enabled', False)

        writing_text = (
            f"✍️ *Yozma ish funksiyasi*\n\n"
            f"Hozirgi holat: ❌ *O'chirilgan*\n\n"
            f"Bu funksiya quyidagilarni o'z ichiga oladi:\n"
            f"• Yozma ishlarni yuklash\n"
            f"• Avtomatik baholash\n"
            f"• Tahlil va statistika\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Yoqish", callback_data='writing_task_on'),
                InlineKeyboardButton("✖️ O'chirilgan", callback_data='writing_task_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            writing_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("❌ Yozma ish funksiyasi o'chirildi!")

    # Handle File Analyzer callbacks
    elif query.data == 'analyzer_full_clean':
        user_data_manager.update_user_field(user_id, 'file_analyzer_mode', True)
        user_data_manager.update_user_field(user_id, 'file_analyzer_operation', 'full_clean')
        
        await query.edit_message_text(
            "🧹 *To'liq tozalash rejimi yoqildi*\n\n"
            "Endi faylni yuboring, men uni to'liq tozalayman:\n"
            "✓ Ortiqcha sarlavhalarni olib tashlayman\n"
            "✓ ID, ism, familiya ustunlarini o'chirayman\n"
            "✓ Faqat 0/1 matritsani ajratib olaman\n"
            "✓ Ustun nomlarini standartlashtiraman\n\n"
            "📤 Excel (.xlsx, .xls) yoki CSV faylni yuboring\n\n"
            "🔙 Chiqish uchun /start yoki 'Ortga' tugmasini bosing",
            parse_mode='Markdown'
        )
        
    elif query.data == 'analyzer_standardize':
        user_data_manager.update_user_field(user_id, 'file_analyzer_mode', True)
        user_data_manager.update_user_field(user_id, 'file_analyzer_operation', 'standardize')
        
        await query.edit_message_text(
            "📝 *Standartlashtirish rejimi yoqildi*\n\n"
            "Endi faylni yuboring, men faqat ustun nomlarini o'zgartiraman:\n"
            "✓ Ustun nomlarini Savol_1, Savol_2, ... formatiga keltiraman\n"
            "✓ Ma'lumotlarga tegmayman\n"
            "✓ Fayl strukturasini saqlayman\n\n"
            "📤 Excel (.xlsx, .xls) yoki CSV faylni yuboring\n\n"
            "🔙 Chiqish uchun /start yoki 'Ortga' tugmasini bosing",
            parse_mode='Markdown'
        )
        
    elif query.data == 'analyzer_back':
        user_data_manager.update_user_field(user_id, 'file_analyzer_mode', False)
        user_data_manager.update_user_field(user_id, 'file_analyzer_operation', None)
        
        await query.edit_message_text(
            "🔙 Bosh menyuga qaytdingiz",
            parse_mode='Markdown'
        )
        
        await query.message.reply_text(
            "🏠 *Bosh menyu*\n\n"
            "Kerakli bo'limni tanlang:",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    
    # Handle subject selection
    elif query.data.startswith('subject_'):
        subject_mapping = {
            'subject_matematika': 'Matematika',
            'subject_fizika': 'Fizika',
            'subject_onatili': 'Ona tili',
            'subject_qoraqalpoqtili': 'Qoraqalpoq tili',
            'subject_rustili': 'Rus tili',
            'subject_tarix': 'Tarix',
            'subject_kimyo': 'Kimyo',
            'subject_biologiya': 'Biologiya',
            'subject_geografiya': 'Geografiya'
        }

        selected_subject = subject_mapping.get(query.data)
        if selected_subject:
            user_data_manager.update_user_field(user_id, 'subject', selected_subject)
            await query.edit_message_text(
                f"✅ Mutaxassislik fani muvaffaqiyatli tanlandi:\n\n"
                f"📚 *{selected_subject}*",
                parse_mode='Markdown'
            )

            await query.message.reply_text(
                "Bosh menyuga qaytdingiz.",
                reply_markup=get_main_keyboard()
            )


async def handle_section_questions_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle section question numbers input"""
    user_id = update.effective_user.id

    # Skip if not configuring sections
    if not context.user_data.get('configuring_sections'):
        return False

    sections_list = context.user_data.get('sections_list', [])
    current_index = context.user_data.get('current_section_index', 0)
    section_questions = context.user_data.get('section_questions', {})
    current_subject = context.user_data.get('current_subject', '')

    if current_index >= len(sections_list):
        return False

    current_section = sections_list[current_index]

    # Parse question numbers
    if text.lower().strip() in ['o\'tkazib', 'otkazib', 'skip']:
        # Skip this section
        question_numbers = []
    else:
        # Try to parse the input
        question_numbers, error_msg = parse_question_numbers(text)

        if error_msg:
            # Show specific error
            await update.message.reply_text(
                f"❌ {error_msg}\n\n"
                "Iltimos, savol raqamlarini to'g'ri formatda kiriting:\n"
                "• Bitta raqam: 5\n"
                "• Vergul bilan ajratilgan: 1,2,3,4,5\n"
                "• Diapazon: 1-10\n"
                "• Aralash: 1-5,7,9,11-15\n\n"
                "Bo'limni o'tkazib yuborish uchun 'o'tkazib' deb yozing."
            )
            return True

        if not question_numbers and text.lower().strip() not in ['o\'tkazib', 'otkazib', 'skip']:
            await update.message.reply_text(
                "❌ Hech qanday to'g'ri raqam topilmadi!\n\n"
                "Iltimos, savol raqamlarini to'g'ri formatda kiriting:\n"
                "• Bitta raqam: 5\n"
                "• Vergul bilan ajratilgan: 1,2,3,4,5\n"
                "• Diapazon: 1-10\n"
                "• Aralash: 1-5,7,9,11-15\n\n"
                "Bo'limni o'tkazib yuborish uchun 'o'tkazib' deb yozing."
            )
            return True

    # Save the question numbers for this section
    section_questions[current_section] = question_numbers
    context.user_data['section_questions'] = section_questions

    # Move to next section
    current_index += 1
    context.user_data['current_section_index'] = current_index

    if current_index < len(sections_list):
        # Ask for next section
        next_section = sections_list[current_index]
        await update.message.reply_text(
            f"✅ {current_section}: Saqlandi\n\n"
            f"*{current_index + 1}-bo'lim: {next_section}*\n\n"
            f"Ushbu bo'limga tegishli savol raqamlarini kiriting.\n"
            f"Masalan: 1-10 yoki 1,2,3,4,5\n\n"
            f"Bo'limni o'tkazib yuborish uchun 'o'tkazib' deb yozing.",
            parse_mode='Markdown'
        )
    else:
        # All sections completed
        # Save to user data
        user_data_manager.update_user_field(user_id, 'section_questions', section_questions)

        # Get pending results if available
        pending_results = context.user_data.get('pending_results')
        pending_general_pdf = context.user_data.get('pending_general_pdf')

        # Show summary
        summary = f"✅ *{current_subject}* fani uchun bo'limlar konfiguratsiyasi tugallandi!\n\n"
        summary += "📋 *Bo'limlar va savol raqamlari:*\n\n"

        for section_name, questions in section_questions.items():
            if questions:
                summary += f"• *{section_name}*: {format_question_list(questions)}\n"
            else:
                summary += f"• *{section_name}*: O'tkazib yuborildi\n"

        await update.message.reply_text(
            summary,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

        # Generate person results with sections if we have pending results
        if pending_results:
            await update.message.reply_text("📊 Bo'limlar bo'yicha natijalar tayyorlanmoqda...")

            pdf_generator = PDFReportGenerator()

            # Generate general person results (without sections)
            person_pdf_path = pdf_generator.generate_person_results_report(
                pending_results,
                filename=f"talabgorlar_natijalari_{user_id}",
                section_questions=None
            )

            # Generate section results in separate PDF
            section_pdf_path = pdf_generator.generate_section_results_report(
                pending_results,
                filename=f"bulimlar_natijalari_{user_id}",
                section_questions=section_questions
            )

            await update.message.reply_text(
                f"✅ *Tahlil tugallandi!*\n\n"
                f"📊 Ishtirokchilar soni: {pending_results['n_persons']}\n"
                f"📝 Itemlar soni: {pending_results['n_items']}\n"
                f"📈 Reliability: {pending_results['reliability']:.3f}\n\n"
                f"PDF hisobotlar yuborilmoqda...",
                parse_mode='Markdown'
            )

            # Send general statistics PDF
            if pending_general_pdf and os.path.exists(pending_general_pdf):
                with open(pending_general_pdf, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=os.path.basename(pending_general_pdf),
                        caption="📊 Umumiy statistika va item parametrlari"
                    )

            # Send general person results PDF
            with open(person_pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(person_pdf_path),
                    caption="👥 Talabgorlar natijalari (Umumiy)"
                )

            # Send section results PDF
            with open(section_pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(section_pdf_path),
                    caption="📋 Bo'limlar bo'yicha natijalar (T-Score)"
                )

        # Clear temporary data
        context.user_data['configuring_sections'] = False
        context.user_data['sections_list'] = None
        context.user_data['current_section_index'] = 0
        context.user_data['section_questions'] = {}
        context.user_data['current_subject'] = None
        context.user_data['pending_results'] = None
        context.user_data['pending_general_pdf'] = None

    return True


def parse_question_numbers(text: str) -> tuple[list, str]:
    """
    Parse question numbers from text input
    Supports formats like: 1-10, 1,2,3,4, or combinations

    Args:
        text: Input text containing question numbers

    Returns:
        Tuple of (list of question numbers, error message if any)
    """
    question_numbers = []
    text = text.strip()

    if not text:
        return ([], "Bo'sh qiymat kiritildi")

    # Split by comma
    parts = text.split(',')
    invalid_parts = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # Check if it's a range (e.g., 1-10)
        if '-' in part:
            range_parts = part.split('-')
            if len(range_parts) != 2:
                invalid_parts.append(part)
                continue

            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())

                if start < 1 or end < 1:
                    invalid_parts.append(part)
                    continue

                if start > end:
                    invalid_parts.append(f"{part} (boshlanish oxirishdan katta)")
                    continue

                question_numbers.extend(range(start, end + 1))
            except ValueError:
                invalid_parts.append(part)
        else:
            # Single number
            try:
                num = int(part)
                if num < 1:
                    invalid_parts.append(f"{num} (musbat bo'lishi kerak)")
                    continue
                question_numbers.append(num)
            except ValueError:
                invalid_parts.append(part)

    # Remove duplicates and sort
    question_numbers = sorted(list(set(question_numbers)))

    # Generate error message if there were invalid parts
    error_msg = ""
    if invalid_parts:
        error_msg = f"Noto'g'ri formatdagi qiymatlar: {', '.join(invalid_parts)}"

    return (question_numbers, error_msg)


def format_question_list(questions: list) -> str:
    """
    Format a list of question numbers into a readable string

    Args:
        questions: List of question numbers

    Returns:
        Formatted string
    """
    if not questions:
        return "Yo'q"

    # Group consecutive numbers into ranges
    questions = sorted(questions)
    ranges = []
    start = questions[0]
    end = questions[0]

    for i in range(1, len(questions)):
        if questions[i] == end + 1:
            end = questions[i]
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = questions[i]
            end = questions[i]

    # Add the last range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


async def handle_profile_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle profile editing text input"""
    user_id = update.effective_user.id
    editing_state = context.user_data.get('editing')

    if editing_state == WAITING_FOR_FULL_NAME:
        user_data_manager.update_user_field(user_id, 'full_name', text)
        await update.message.reply_text(
            f"✅ Ism va familiya muvaffaqiyatli o'zgartirildi: *{text}*",
            parse_mode='Markdown'
        )
        context.user_data['editing'] = None

    elif editing_state == WAITING_FOR_SUBJECT:
        user_data_manager.update_user_field(user_id, 'subject', text)
        await update.message.reply_text(
            f"✅ Mutaxassislik muvaffaqiyatli o'zgartirildi: *{text}*",
            parse_mode='Markdown'
        )
        context.user_data['editing'] = None

    elif editing_state == WAITING_FOR_BIO:
        user_data_manager.update_user_field(user_id, 'bio', text)
        await update.message.reply_text(
            f"✅ Bio muvaffaqiyatli o'zgartirildi: *{text}*",
            parse_mode='Markdown'
        )
        context.user_data['editing'] = None

    return editing_state is not None


def get_settings_keyboard(user_id: int = None):
    """Create keyboard for Settings section"""
    keyboard = [
        [KeyboardButton("📚 Mutaxassislik fanini tanlash")],
        [KeyboardButton("📊 Fan bo'limlari bo'yicha natijalash")],
        [KeyboardButton("✍️ Yozma ish funksiyasi")],
        [KeyboardButton("◀️ Ortga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Settings button"""
    user_id = update.effective_user.id
    settings_text = (
        "⚙️ *Sozlamalar*\n\n"
        "Quyidagi sozlamalardan birini tanlang:"
    )
    await update.message.reply_text(
        settings_text, 
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard(user_id)
    )


async def handle_select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Select Subject button"""
    subject_text = (
        "📚 *Mutaxassislik fanini tanlash*\n\n"
        "Quyidagi fanlardan birini tanlang:"
    )

    # Create inline keyboard with 9 subjects
    keyboard = [
        [InlineKeyboardButton("📐 Matematika", callback_data='subject_matematika'),
         InlineKeyboardButton("⚛️ Fizika", callback_data='subject_fizika')],
        [InlineKeyboardButton("📝 Ona tili", callback_data='subject_onatili'),
         InlineKeyboardButton("📚 Qoraqalpoq tili", callback_data='subject_qoraqalpoqtili')],
        [InlineKeyboardButton("🇷🇺 Rus tili", callback_data='subject_rustili'),
         InlineKeyboardButton("📜 Tarix", callback_data='subject_tarix')],
        [InlineKeyboardButton("🧪 Kimyo", callback_data='subject_kimyo'),
         InlineKeyboardButton("🧬 Biologiya", callback_data='subject_biologiya')],
        [InlineKeyboardButton("🌍 Geografiya", callback_data='subject_geografiya')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        subject_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_section_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Section Results button"""
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)

    # Get current state (default is off)
    section_results_enabled = user_data.get('section_results_enabled', False)

    status_icon = "✅" if section_results_enabled else "❌"
    status_text = "Yoqilgan" if section_results_enabled else "O'chirilgan"

    section_text = (
        f"📊 *Fan bo'limlari bo'yicha natijalash*\n\n"
        f"Hozirgi holat: {status_icon} *{status_text}*\n\n"
        f"Bu funksiya sizga quyidagilarni beradi:\n"
        f"• Har bir bo'lim bo'yicha natijalar\n"
        f"• Bo'limlar qiyoslash\n"
        f"• Talabgorlar yutuqlari tahlili\n\n"
        f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
    )

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Yoqish" if not section_results_enabled else "✔️ Yoqilgan",
                callback_data='section_results_on'
            ),
            InlineKeyboardButton(
                "❌ O'chirish" if section_results_enabled else "✖️ O'chirilgan",
                callback_data='section_results_off'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        section_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_configure_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Configure Sections button"""
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)

    subject = user_data.get('subject', '')
    section_results_enabled = user_data.get('section_results_enabled', False)

    if not section_results_enabled:
        await update.message.reply_text(
            "❌ Bo'limlar bo'yicha natijalash funksiyasi o'chirilgan!\n\n"
            "Avval 'Fan bo'limlari bo'yicha natijalash' dan funksiyani yoqing.",
            reply_markup=get_settings_keyboard(user_id)
        )
        return

    if not subject:
        await update.message.reply_text(
            "❌ Mutaxassislik fani tanlanmagan!\n\n"
            "Avval 'Mutaxassislik fanini tanlash' dan fanini tanlang.",
            reply_markup=get_settings_keyboard(user_id)
        )
        return

    if not has_sections(subject):
        await update.message.reply_text(
            f"❌ {subject} fani uchun bo'limlar ma'lumotlari mavjud emas!",
            reply_markup=get_settings_keyboard(user_id)
        )
        return

    # Start section configuration
    sections = get_sections(subject)
    context.user_data['configuring_sections'] = True
    context.user_data['current_subject'] = subject
    context.user_data['sections_list'] = sections
    context.user_data['current_section_index'] = 0
    context.user_data['section_questions'] = {}

    await update.message.reply_text(
        f"🔧 *{subject}* fani uchun bo'limlarni sozlash:\n\n"
        f"Jami {len(sections)} ta bo'lim mavjud.\n\n"
        f"*1-bo'lim: {sections[0]}*\n\n"
        f"Ushbu bo'limga tegishli savol raqamlarini kiriting.\n\n"
        f"Formatlar:\n"
        f"• Bitta raqam: 5\n"
        f"• Vergul bilan ajratilgan: 1,2,3,4,5\n"
        f"• Diapazon: 1-10\n"
        f"• Aralash: 1-5,7,9,11-15\n\n"
        f"Bo'limni o'tkazib yuborish uchun 'o'tkazib' deb yozing.",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def handle_writing_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Writing Task button"""
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)

    # Get current state (default is off)
    writing_task_enabled = user_data.get('writing_task_enabled', False)

    status_icon = "✅" if writing_task_enabled else "❌"
    status_text = "Yoqilgan" if writing_task_enabled else "O'chirilgan"

    writing_text = (
        f"✍️ *Yozma ish funksiyasi*\n\n"
        f"Hozirgi holat: {status_icon} *{status_text}*\n\n"
        f"Bu funksiya quyidagilarni o'z ichiga oladi:\n"
        f"• Yozma ishlarni yuklash\n"
        f"• Avtomatik baholash\n"
        f"• Tahlil va statistika\n\n"
        f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
    )

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Yoqish" if not writing_task_enabled else "✔️ Yoqilgan",
                callback_data='writing_task_on'
            ),
            InlineKeyboardButton(
                "❌ O'chirish" if writing_task_enabled else "✖️ O'chirilgan",
                callback_data='writing_task_off'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        writing_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Students button - show list of students"""
    user_id = update.effective_user.id
    students = student_data_manager.get_all_students(user_id)

    if not students:
        students_text = (
            "👥 <b>O'quvchilar ro'yxati</b>\n\n"
            "Hozircha ro'yxatda o'quvchilar yo'q.\n\n"
            "Yangi o'quvchi qo'shish uchun pastdagi tugmani bosing."
        )
        keyboard = [
            [KeyboardButton("➕ Yangi o'quvchi qo'shish")],
            [KeyboardButton("◀️ Ortga")]
        ]
    else:
        students_text = f"👥 <b>O'quvchilar ro'yxati</b> ({len(students)} ta)\n\n"

        for student in students:
            full_name = student.get('full_name', "Noma'lum")
            students_text += f"👤 <b>{full_name}</b>\n"
            if student.get('telegram_username'):
                students_text += f"   📱 @{student.get('telegram_username')}\n"
            if student.get('parent_telegram'):
                students_text += f"   👨‍👩‍👦 Ota-ona: @{student.get('parent_telegram')}\n"
            students_text += "\n"

        keyboard = [
            [KeyboardButton("➕ Yangi o'quvchi qo'shish")],
            [KeyboardButton("✏️ O'quvchini tahrirlash"), KeyboardButton("🗑 O'quvchini o'chirish")],
            [KeyboardButton("◀️ Ortga")]
        ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(students_text, parse_mode='HTML', reply_markup=reply_markup)


def get_other_keyboard():
    """Create keyboard for 'Boshqa' section"""
    keyboard = [
        [KeyboardButton("📁 File Analyzer")],
        [KeyboardButton("📝 Ommaviy test o'tkazish")],
        [KeyboardButton("📊 Statistika")],
        [KeyboardButton("👥 Hamjamiyat")],
        [KeyboardButton("💬 Adminga murojaat")],
        [KeyboardButton("◀️ Ortga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Other button"""
    other_text = (
        "ℹ️ *Boshqa bo'lim*\n\n"
        "Quyidagi bo'limlardan birini tanlang:"
    )
    await update.message.reply_text(
        other_text, 
        parse_mode='Markdown',
        reply_markup=get_other_keyboard()
    )


async def handle_public_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Public Test button"""
    test_text = (
        "📝 *Ommaviy test o'tkazish*\n\n"
        "Bu bo'limda siz:\n"
        "• Ommaviy testlar yaratishingiz\n"
        "• Testlarni tarqatishingiz\n"
        "• Natijalarni yig'ishingiz mumkin\n\n"
        "🔜 Tez orada faollashitiriladi!"
    )
    await update.message.reply_text(test_text, parse_mode='Markdown')


async def handle_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Statistics button"""
    stats_text = (
        "📊 *Statistika*\n\n"
        "Bu yerda siz:\n"
        "• Umumiy tahlil statistikasini\n"
        "• Talabgorlar o'sish dinamikasini\n"
        "• Test natijalarini ko'rishingiz mumkin\n\n"
        "🔜 Tez orada faollashtiriladi!"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def handle_community(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Community button"""
    community_text = (
        "👥 *Hamjamiyat*\n\n"
        "Bizning hamjamiyatga qo'shiling:\n"
        "• Tajriba almashish\n"
        "• Savollar berish\n"
        "• Yangiliklar va yangilanishlar\n\n"
        "🔜 Tez orada faollashtiriladi!"
    )
    await update.message.reply_text(community_text, parse_mode='Markdown')


async def handle_contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Contact Admin button"""
    contact_text = (
        "💬 *Adminga murojaat*\n\n"
        "Savollaringiz yoki takliflaringiz bo'lsa,\n"
        "quyidagi ma'lumotlardan foydalaning:\n\n"
        "📧 Email: support@raschbot.uz\n"
        "📱 Telegram: @raschbot_admin\n\n"
        "Tez orada javob beramiz! 😊"
    )
    await update.message.reply_text(contact_text, parse_mode='Markdown')


async def handle_file_analyzer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle File Analyzer button - show cleaning options"""
    user_id = update.effective_user.id
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("🧹 To'liq tozalash", callback_data="analyzer_full_clean")],
        [InlineKeyboardButton("📝 Faqat standartlashtirish", callback_data="analyzer_standardize")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="analyzer_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    analyzer_text = (
        "📁 *File Analyzer*\n\n"
        "Qaysi operatsiyani bajarishni xohlaysiz?\n\n"
        "🧹 *To'liq tozalash:*\n"
        "  • Ortiqcha sarlavhalarni olib tashlaydi\n"
        "  • ID, ism, familiya ustunlarini o'chiradi\n"
        "  • Faqat 0/1 matritsani ajratib oladi\n"
        "  • Ustun nomlarini standartlashtiradi\n\n"
        "📝 *Faqat standartlashtirish:*\n"
        "  • Faqat ustun nomlarini o'zgartiradi\n"
        "  • Savol_1, Savol_2, ... formatiga keltiradi\n"
        "  • Ma'lumotlarga tegmaydi\n\n"
        "Operatsiyani tanlang:"
    )
    await update.message.reply_text(analyzer_text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Back button - return to main menu"""
    user_id = update.effective_user.id
    
    # Disable file analyzer mode
    user_data_manager.update_user_field(user_id, 'file_analyzer_mode', False)
    user_data_manager.update_user_field(user_id, 'file_analyzer_operation', None)
    
    # Clear any ongoing operations
    context.user_data['editing'] = None
    context.user_data['adding_student'] = None
    context.user_data['student_temp'] = None

    welcome_text = (
        "🏠 *Bosh menyu*\n\n"
        "Kerakli bo'limni tanlang:"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def handle_add_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding new student"""
    context.user_data['adding_student'] = WAITING_FOR_STUDENT_NAME
    context.user_data['student_temp'] = {}

    await update.message.reply_text(
        "➕ *Yangi o'quvchi qo'shish*\n\n"
        "O'quvchining ism va familiyasini kiriting:",
        parse_mode='Markdown'
    )


async def handle_edit_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start editing student"""
    user_id = update.effective_user.id
    students = student_data_manager.get_all_students(user_id)

    if not students:
        await update.message.reply_text("❌ O'quvchilar ro'yxati bo'sh!")
        return

    text = "✏️ *Tahrirlash uchun o'quvchi ID raqamini kiriting:*\n\n"
    for student in students:
        full_name = student.get('full_name', "Noma'lum")
        text += f"{student['id']}. {full_name}\n"

    context.user_data['editing_student'] = True
    await update.message.reply_text(text, parse_mode='Markdown')


async def handle_delete_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start deleting student"""
    user_id = update.effective_user.id
    students = student_data_manager.get_all_students(user_id)

    if not students:
        await update.message.reply_text("❌ O'quvchilar ro'yxati bo'sh!")
        return

    text = "🗑 *O'chirish uchun o'quvchi ID raqamini kiriting:*\n\n"
    for student in students:
        full_name = student.get('full_name', "Noma'lum")
        text += f"{student['id']}. {full_name}\n"

    context.user_data['deleting_student'] = True
    await update.message.reply_text(text, parse_mode='Markdown')


async def handle_student_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle student data input"""
    user_id = update.effective_user.id

    # Handle adding new student
    if context.user_data.get('adding_student') == WAITING_FOR_STUDENT_NAME:
        context.user_data['student_temp']['full_name'] = text
        context.user_data['adding_student'] = WAITING_FOR_STUDENT_TELEGRAM
        await update.message.reply_text(
            "📱 O'quvchining Telegram username'ini kiriting\n"
            "(@ belgisisiz, masalan: johndoe)\n\n"
            "Agar yo'q bo'lsa, 'yo'q' deb yozing:"
        )
        return True

    elif context.user_data.get('adding_student') == WAITING_FOR_STUDENT_TELEGRAM:
        if text.lower() != "yo'q" and text.lower() != "yoq":
            context.user_data['student_temp']['telegram_username'] = text.replace('@', '')
        context.user_data['adding_student'] = WAITING_FOR_PARENT_TELEGRAM
        await update.message.reply_text(
            "👨‍👩‍👦 Ota-onaning Telegram username'ini kiriting\n"
            "(@ belgisisiz, masalan: parent123)\n\n"
            "Agar yo'q bo'lsa, 'yo'q' deb yozing:"
        )
        return True

    elif context.user_data.get('adding_student') == WAITING_FOR_PARENT_TELEGRAM:
        if text.lower() != "yo'q" and text.lower() != "yoq":
            context.user_data['student_temp']['parent_telegram'] = text.replace('@', '')

        # Save student
        student_data = context.user_data['student_temp']
        student_id = student_data_manager.add_student(user_id, student_data)

        await update.message.reply_text(
            f"✅ O'quvchi muvaffaqiyatli qo'shildi!\n\n"
            f"👤 *{student_data.get('full_name')}*\n"
            f"ID: {student_id}",
            parse_mode='Markdown'
        )

        # Clear temp data
        context.user_data['adding_student'] = None
        context.user_data['student_temp'] = None

        # Show updated list
        await handle_students(update, context)
        return True

    # Handle editing student
    elif context.user_data.get('editing_student'):
        try:
            student_id = int(text)
            student = student_data_manager.get_student(user_id, student_id)

            if not student:
                # Increment error count
                error_count = context.user_data.get('edit_error_count', 0) + 1
                context.user_data['edit_error_count'] = error_count

                if error_count >= 3:
                    await update.message.reply_text(
                        "❌ 3 marta noto'g'ri urinish. Jarayon bekor qilindi.",
                        reply_markup=get_main_keyboard()
                    )
                    context.user_data['editing_student'] = None
                    context.user_data['edit_error_count'] = 0
                    return True

                await update.message.reply_text(
                    f"❌ Bunday ID'li o'quvchi topilmadi!\n"
                    f"Urinish: {error_count}/3"
                )
                return True

            # Reset error count on success
            context.user_data['edit_error_count'] = 0
            context.user_data['editing_student_id'] = student_id
            context.user_data['student_temp'] = student.copy()
            context.user_data['editing_student'] = None
            context.user_data['adding_student'] = WAITING_FOR_STUDENT_NAME

            await update.message.reply_text(
                f"✏️ O'quvchini tahrirlash: *{student.get('full_name')}*\n\n"
                f"Yangi ism va familiyani kiriting\n"
                f"(hozirgi: {student.get('full_name')}):",
                parse_mode='Markdown'
            )
            return True
        except ValueError:
            # Increment error count
            error_count = context.user_data.get('edit_error_count', 0) + 1
            context.user_data['edit_error_count'] = error_count

            if error_count >= 3:
                await update.message.reply_text(
                    "❌ 3 marta noto'g'ri urinish. Jarayon bekor qilindi.",
                    reply_markup=get_main_keyboard()
                )
                context.user_data['editing_student'] = None
                context.user_data['edit_error_count'] = 0
                return True

            await update.message.reply_text(
                f"❌ Iltimos, raqam kiriting!\n"
                f"Urinish: {error_count}/3"
            )
            return True

    # Handle deleting student
    elif context.user_data.get('deleting_student'):
        try:
            student_id = int(text)
            student = student_data_manager.get_student(user_id, student_id)

            if not student:
                # Increment error count
                error_count = context.user_data.get('delete_error_count', 0) + 1
                context.user_data['delete_error_count'] = error_count

                if error_count >= 3:
                    await update.message.reply_text(
                        "❌ 3 marta noto'g'ri urinish. Jarayon bekor qilindi.",
                        reply_markup=get_main_keyboard()
                    )
                    context.user_data['deleting_student'] = None
                    context.user_data['delete_error_count'] = 0
                    return True

                await update.message.reply_text(
                    f"❌ Bunday ID'li o'quvchi topilmadi!\n"
                    f"Urinish: {error_count}/3"
                )
                return True

            # Reset error count on success
            context.user_data['delete_error_count'] = 0
            student_data_manager.delete_student(user_id, student_id)
            await update.message.reply_text(
                f"✅ O'quvchi o'chirildi: *{student.get('full_name')}*",
                parse_mode='Markdown'
            )

            context.user_data['deleting_student'] = None
            await handle_students(update, context)
            return True
        except ValueError:
            # Increment error count
            error_count = context.user_data.get('delete_error_count', 0) + 1
            context.user_data['delete_error_count'] = error_count

            if error_count >= 3:
                await update.message.reply_text(
                    "❌ 3 marta noto'g'ri urinish. Jarayon bekor qilindi.",
                    reply_markup=get_main_keyboard()
                )
                context.user_data['deleting_student'] = None
                context.user_data['delete_error_count'] = 0
                return True

            await update.message.reply_text(
                f"❌ Iltimos, raqam kiriting!\n"
                f"Urinish: {error_count}/3"
            )
            return True

    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    message_text = update.message.text

    # Handle "Ortga" button - cancel any ongoing operations
    if message_text == "◀️ Ortga":
        # Check if there was an ongoing operation
        was_operation = (
            context.user_data.get('editing') or 
            context.user_data.get('adding_student') or 
            context.user_data.get('editing_student') or 
            context.user_data.get('deleting_student') or
            context.user_data.get('configuring_sections')
        )

        # Clear all temporary states
        context.user_data['editing'] = None
        context.user_data['adding_student'] = None
        context.user_data['editing_student'] = None
        context.user_data['deleting_student'] = None
        context.user_data['student_temp'] = None
        context.user_data['editing_student_id'] = None
        context.user_data['edit_error_count'] = 0
        context.user_data['delete_error_count'] = 0
        context.user_data['configuring_sections'] = False
        context.user_data['sections_list'] = None
        context.user_data['current_section_index'] = 0
        context.user_data['section_questions'] = {}
        context.user_data['current_subject'] = None

        # Show cancellation message if there was an operation
        if was_operation:
            await update.message.reply_text(
                "❌ Amal bekor qilindi.",
                reply_markup=get_main_keyboard()
            )
        else:
            await handle_back(update, context)
        return

    # Check if user is configuring sections
    if context.user_data.get('configuring_sections'):
        handled = await handle_section_questions_input(update, context, message_text)
        if handled:
            return

    # Check if user is editing profile
    if context.user_data.get('editing'):
        handled = await handle_profile_edit(update, context, message_text)
        if handled:
            return

    # Check if user is managing students
    if context.user_data.get('adding_student') or context.user_data.get('editing_student') or context.user_data.get('deleting_student'):
        handled = await handle_student_input(update, context, message_text)
        if handled:
            return

    # Handle main keyboard button presses
    if message_text == "👤 Profil":
        await handle_profile(update, context)
    elif message_text == "⚙️ Sozlamalar":
        await handle_settings(update, context)
    elif message_text == "👥 O'quvchilar":
        await handle_students(update, context)
    elif message_text == "ℹ️ Boshqa":
        await handle_other(update, context)
    # Handle 'Boshqa' section buttons
    elif message_text == "📁 File Analyzer":
        await handle_file_analyzer(update, context)
    elif message_text == "📝 Ommaviy test o'tkazish":
        await handle_public_test(update, context)
    elif message_text == "📊 Statistika":
        await handle_statistics(update, context)
    elif message_text == "👥 Hamjamiyat":
        await handle_community(update, context)
    elif message_text == "💬 Adminga murojaat":
        await handle_contact_admin(update, context)
    elif message_text == "◀️ Ortga":
        await handle_back(update, context)
    # Handle student management buttons
    elif message_text == "➕ Yangi o'quvchi qo'shish":
        await handle_add_student(update, context)
    elif message_text == "✏️ O'quvchini tahrirlash":
        await handle_edit_student(update, context)
    elif message_text == "🗑 O'quvchini o'chirish":
        await handle_delete_student(update, context)
    # Handle settings section buttons
    elif message_text == "📚 Mutaxassislik fanini tanlash":
        await handle_select_subject(update, context)
    elif message_text == "📊 Fan bo'limlari bo'yicha natijalash":
        await handle_section_results(update, context)
    elif message_text == "✍️ Yozma ish funksiyasi":
        await handle_writing_task(update, context)
    else:
        await update.message.reply_text(
            "📎 Ma'lumotlar faylini yuboring!\n\n"
            "CSV yoki Excel formatdagi faylni yuboring. "
            "Yordam kerak bo'lsa /help buyrug'ini yuboring."
        )