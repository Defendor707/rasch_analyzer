import os
import pandas as pd
import fitz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils.rasch_analysis import RaschAnalyzer
from bot.utils.pdf_generator import PDFReportGenerator
from bot.utils.user_data import UserDataManager
from bot.utils.student_data import StudentDataManager
from bot.utils.subject_sections import get_sections, has_sections
from bot.utils.data_cleaner import DataCleaner
from bot.utils.test_manager import TestManager
from bot.utils.payment_manager import PaymentManager
from bot.utils.bonus_manager import BonusManager # Import BonusManager
from bot.utils.answer_parser import parse_answer_string, generate_option_labels, format_answer_example
# from bot.utils.ai_analyzer import AIAnalyzer
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Initialize user data manager
user_data_manager = UserDataManager()
student_data_manager = StudentDataManager()
test_manager = TestManager()
payment_manager = PaymentManager()
bonus_manager = BonusManager() # Initialize BonusManager

# Conversation states
WAITING_FOR_FULL_NAME = 1
WAITING_FOR_BIO = 2
WAITING_FOR_SUBJECT = 3
WAITING_FOR_STUDENT_NAME = 4
WAITING_FOR_STUDENT_TELEGRAM = 5
WAITING_FOR_PARENT_TELEGRAM = 6
WAITING_FOR_SECTION_QUESTIONS = 7
WAITING_FOR_TEST_NAME = 8
WAITING_FOR_TIME_RESTRICTION_CHOICE = 9
WAITING_FOR_TEST_START_DATE = 10
WAITING_FOR_TEST_START_TIME = 11
WAITING_FOR_TEST_DURATION = 12
WAITING_FOR_QUESTION_TEXT = 13
WAITING_FOR_QUESTION_OPTIONS = 14
WAITING_FOR_CORRECT_ANSWER = 15
WAITING_FOR_ADMIN_MESSAGE = 16
WAITING_FOR_QUESTION_FILE = 17
WAITING_FOR_CORRECT_ANSWER_FROM_FILE = 18
WAITING_FOR_PDF_QUESTION_FILE = 19
WAITING_FOR_QUESTION_COUNT = 20
WAITING_FOR_PDF_CORRECT_ANSWER = 21
WAITING_FOR_ALL_PDF_ANSWERS = 22
WAITING_FOR_PHONE = 23
WAITING_FOR_EXPERIENCE = 24
WAITING_FOR_PHOTO = 25
WAITING_FOR_PAID_TEST_CHOICE = 26
WAITING_FOR_TEST_PRICE = 27


def get_main_keyboard():
    """Create main reply keyboard with 3 buttons"""
    keyboard = [
        [KeyboardButton("📝 Online test o'tkazish")],
        [KeyboardButton("⚙️ Sozlamalar"), KeyboardButton("ℹ️ Boshqa")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart bot - clear all states and return to main menu"""
    user_id = update.effective_user.id

    # Clear all user states in database
    user_data_manager.update_user_field(user_id, 'file_analyzer_mode', False)
    user_data_manager.update_user_field(user_id, 'file_analyzer_operation', None)
    user_data_manager.update_user_field(user_id, 'waiting_for_photo', False)
    user_data_manager.update_user_field(user_id, 'waiting_for_contact', False)
    user_data_manager.update_user_field(user_id, 'waiting_for_experience', False)

    # Clear all context data
    if 'test_creation' in context.user_data:
        del context.user_data['test_creation']
    if 'test_id' in context.user_data:
        del context.user_data['test_id']
    if 'question_answers' in context.user_data:
        del context.user_data['question_answers']
    if 'pdf_file_path' in context.user_data:
        del context.user_data['pdf_file_path']

    context.user_data.clear()

    # Send restart message
    await update.message.reply_text(
        "🔄 *Bot qayta ishga tushirildi*\n\n"
        "Barcha davom etayotgan jarayonlar bekor qilindi.\n"
        "Bosh menyuga qaytdingiz.",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

    logger.info(f"Bot restarted by user {user_id}")


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
        f"👋 Assalomu alaykum, *{full_name}*!\n\n"
        "🎓 Rasch Analyzer Botga xush kelibsiz!\n\n"
        "/help buyrug'i orqali bot bilan tanishib chiqing!"
    )

    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

    # Send second message separately
    await update.message.reply_text(
        "📊 Excel faylini yuborishingiz mumkin"
    )


async def perform_test_rasch_analysis(message, context, test_id: str):
    """Perform Rasch analysis on test results and send PDF report"""
    try:
        # Get test results matrix
        test_results = test_manager.get_test_results_matrix(test_id)

        if not test_results:
            await message.reply_text("❌ Test natijalarini olishda xatolik yuz berdi!")
            return

        if test_results['n_participants'] < 3:
            await message.reply_text(
                "❌ Rasch tahlili uchun kamida 3 ta ishtirokchi kerak!\n\n"
                f"Hozirgi ishtirokchilar: {test_results['n_participants']} ta"
            )
            return

        await message.reply_text(
            f"⏳ Tahlil jarayoni boshlandi...\n\n"
            f"📊 Test: {test_results['test_name']}\n"
            f"👥 Ishtirokchilar: {test_results['n_participants']} ta\n"
            f"📝 Savollar: {test_results['n_questions']} ta\n\n"
            f"📈 Tahlil qilinmoqda..."
        )

        # Create DataFrame from response matrix
        import pandas as pd
        data = pd.DataFrame(
            test_results['matrix'],
            columns=test_results['item_names']
        )

        # Get student names from student_ids
        from bot.utils.student_data import StudentDataManager
        student_manager = StudentDataManager()
        teacher_id = message.chat.id
        person_names = []
        for student_id in test_results.get('student_ids', []):
            student = student_manager.get_student(teacher_id, student_id)
            if student and student.get('full_name'):
                person_names.append(student['full_name'])
            else:
                # Fallback to student_id if name not found
                person_names.append(f"Talabgor {student_id}")

        # Perform Rasch analysis
        analyzer = RaschAnalyzer()
        results = analyzer.fit(data, person_names=person_names if person_names else None)

        # Generate PDF reports
        pdf_generator = PDFReportGenerator()
        user_id = message.chat.id

        # General statistics report
        general_pdf_path = pdf_generator.generate_report(
            results,
            filename=f"test_{test_id}_umumiy_{user_id}"
        )

        # Person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename=f"test_{test_id}_talabgorlar_{user_id}"
        )

        await message.reply_text(
            f"✅ *Rasch tahlili tugallandi!*\n\n"
            f"📋 Test: {test_results['test_name']}\n"
            f"📚 Fan: {test_results['test_subject']}\n"
            f"👥 Talabgorlar: {results['n_persons']}\n"
            f"📝 Savollar: {results['n_items']}\n"
            f"📈 Reliability: {results['reliability']:.3f}\n\n"
            f"PDF hisobotlar yuborilmoqda...",
            parse_mode='Markdown'
        )

        # Send general statistics PDF
        if general_pdf_path and os.path.exists(general_pdf_path):
            with open(general_pdf_path, 'rb') as pdf_file:
                await message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(general_pdf_path),
                    caption="📊 Umumiy statistika"
                )

        # Send person results PDF
        with open(person_pdf_path, 'rb') as pdf_file:
            await message.reply_document(
                document=pdf_file,
                filename=os.path.basename(person_pdf_path),
                caption="👥 Talabgorlar natijalari"
            )

        await message.reply_text(
            "✅ Barcha hisobotlar yuborildi!\n\n"
            "Natijalarni tahlil qilishingiz mumkin.",
            reply_markup=get_main_keyboard()
        )

        logger.info(f"Test {test_id} Rasch analysis completed successfully")

    except Exception as e:
        import traceback
        logger.error(f"Error in test Rasch analysis: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        await message.reply_text(
            f"❌ Tahlilda xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos, testda kamida 3 ta ishtirokchi va to'g'ri javoblar mavjudligini tekshiring."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when the command /help is issued"""
    help_message = (
        "📖 *Yordam*\n\n"
        "*Fayl talablari:*\n"
        "• Format: CSV (.csv) yoki Excel (.xlsx, .xls)\n"
        "• Qatorlar: Har bir qator - bitta ishtirokchi\n"
        "• Ustunlar: Har bir ustun - bitta savol/item\n"
        "• Qiymatlar: Faqat 0 va 1 (dikotomik ma'lumotlar)\n\n"
        "*Misol ma'lumotlar strukturasi:*\n"
        "```\n"
        "talabgorlar, Item1, Item2, Item3, Item4\n"
        "talabgor1,   1,     0,     1,     1\n"
        "talabgor2,   0,     0,     0,     1\n"
        "talabgor3,   1,     1,     1,     1\n"
        "```\n\n"
        "*Natijalar:*\n"
        "PDF hisobotda quyidagilar bo'ladi:\n"
        "✓ Item difficulty parametrlari\n"
        "✓ Person ability ko'rsatkichlari\n"
        "✓ Reliability (ishonchlilik)\n"
        "✓ Deskriptiv statistika\n\n"
        "Savol bo'lsa hamjamiyatdan javob topasiz, fayl yuboring va tahlilni boshlaymiz!"
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
            filename="statistika"
        )

        # Get section questions if configured
        user_data = user_data_manager.get_user_data(user_id)
        section_questions = user_data.get('section_questions')
        section_results_enabled = user_data.get('section_results_enabled', False)

        # Generate person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename="talabgorlar-statistikasi",
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
                filename="bulimlar-statistikasi",
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


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads for profile"""
    user_id = update.effective_user.id

    # Check if user is uploading profile photo
    if context.user_data.get('editing') == WAITING_FOR_PHOTO:
        # Get the largest photo
        photo = update.message.photo[-1]
        file_id = photo.file_id

        # Save photo file_id to user data
        user_data_manager.update_user_field(user_id, 'profile_photo_id', file_id)

        await update.message.reply_text(
            "✅ Profil rasmi muvaffaqiyatli saqlandi!",
            reply_markup=get_main_keyboard()
        )
        context.user_data['editing'] = None
        return

    # If not editing, just acknowledge
    await update.message.reply_text(
        "📸 Rasm qabul qilindi. Profil rasmini o'zgartirish uchun:\n"
        "👤 Profil → 📸 Foto"
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded document files"""
    document = update.message.document
    user_id = update.effective_user.id

    file_extension = os.path.splitext(document.file_name)[1].lower()

    # Check if user is uploading PDF questions file for test
    creating_state = context.user_data.get('creating_test')
    if creating_state == WAITING_FOR_PDF_QUESTION_FILE:
        if file_extension != '.pdf':
            await update.message.reply_text(
                "❌ Iltimos, PDF faylini yuboring!"
            )
            return
        await handle_pdf_question_file_upload(update, context, document)
        return

    # Support both .xlsx and .xls Excel formats
    if file_extension not in ['.csv', '.xlsx', '.xls']:
        await update.message.reply_text(
            "❌ Noto'g'ri fayl formati!\n\n"
            "Iltimos, CSV (.csv) yoki Excel (.xlsx, .xls) formatdagi fayl yuboring."
        )
        return

    # Check if user is uploading questions file for test
    if creating_state == WAITING_FOR_QUESTION_FILE:
        await handle_question_file_upload(update, context, document, file_extension)
        return

    # Check if user is in File Analyzer mode
    user_data = user_data_manager.get_user_data(user_id)
    file_analyzer_mode = user_data.get('file_analyzer_mode', False)

    if file_analyzer_mode:
        # FILE ANALYZER MODE: Full clean the file
        await update.message.reply_text("🧹 File Analyzer: Fayl to'liq tozalanmoqda va standartlashtirilmoqda...")

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
            elif file_extension == '.xls':
                # Try xlrd engine first for old Excel format
                try:
                    data = pd.read_excel(file_path, engine='xlrd')
                except Exception as xlrd_error:
                    # If xlrd fails, try openpyxl as fallback
                    logger.warning(f"xlrd failed for .xls file, trying openpyxl: {str(xlrd_error)}")
                    try:
                        data = pd.read_excel(file_path, engine='openpyxl')
                    except Exception as openpyxl_error:
                        raise Exception(
                            f"Faylni o'qib bo'lmadi. xlrd xatoligi: {str(xlrd_error)}. "
                            f"openpyxl xatoligi: {str(openpyxl_error)}"
                        )
            else:
                # Use openpyxl engine for new Excel format (.xlsx)
                data = pd.read_excel(file_path, engine='openpyxl')

            cleaner = DataCleaner()

            # Perform full cleaning
            processed_data, metadata = cleaner.clean_data(data)
            report = cleaner.get_cleaning_report(metadata)
            output_prefix = "cleaned"
            operation = "cleaning"
            success_message = "✅ Tozalangan va standartlashtirilgan fayl tayyor!\n\n" \
                            "Fayl to'liq tozalandi va standartlashtirildi.\n" \
                            "Endi uni tahlil qilish uchun qayta yuboring yoki /start orqali chiqing."

            # Send report
            await update.message.reply_text(report)

            # Save processed file
            processed_file_path = os.path.join(upload_dir, f"{output_prefix}_{user_id}_{document.file_name}")
            if file_extension == '.csv':
                processed_data.to_csv(processed_file_path, index=False)
            else:
                # Excel fayllarini openpyxl bilan saqlash
                processed_data.to_excel(processed_file_path, index=False, engine='openpyxl')

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

    # NORMAL MODE: Check payment and analyze the file
    await update.message.reply_text("⏳ Fayl qabul qilindi...")

    try:
        file = await context.bot.get_file(document.file_id)

        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, f"{user_id}_{document.file_name}")
        await file.download_to_drive(file_path)

        # Save file info for later use
        context.user_data['pending_analysis_file'] = file_path
        context.user_data['pending_analysis_filename'] = document.file_name
        context.user_data['pending_file_extension'] = file_extension

        # Check if payment is required
        if payment_manager.is_payment_enabled():
            # Send payment invoice
            from bot.handlers.payment_handlers import create_payment_invoice
            await create_payment_invoice(update, context, document.file_name)
        else:
            # Payment disabled - proceed directly to analysis
            await update.message.reply_text(
                "🎉 Xizmat hozir tekin!\n\n"
                "📊 Tahlil jarayoni boshlandi..."
            )
            # Set payment as completed to skip payment check
            context.user_data['payment_completed'] = True
            context.user_data['paid_file_name'] = document.file_name

            # Perform analysis directly
            await perform_analysis_after_payment(update.message, context)

    except Exception as e:
        logger.error(f"Error uploading file for user {user_id}: {str(e)}")
        await update.message.reply_text(
            f"❌ Faylni yuklashda xatolik: {str(e)}\n\n"
            "Iltimos, qayta urinib ko'ring."
        )


async def perform_analysis_after_payment(message, context: ContextTypes.DEFAULT_TYPE):
    """Perform Rasch analysis after successful payment"""
    user_id = message.chat.id

    file_path = context.user_data.get('pending_analysis_file')
    file_extension = context.user_data.get('pending_file_extension')

    if not file_path or not os.path.exists(file_path):
        await message.reply_text("❌ Fayl topilmadi. Iltimos, qayta fayl yuboring.")
        return

    try:
        if file_extension == '.csv':
            try:
                data = pd.read_csv(file_path)
            except Exception:
                data = pd.read_csv(file_path, encoding='latin-1')
        else:
            data = pd.read_excel(file_path)

        # Birinchi ustun "Talabgor" bo'lsa, uni olib tashlash kerak
        # File Analyzer tozalangan faylda birinchi ustun har doim ism ustuni
        participant_column = None
        if len(data.columns) > 0:
            first_col = data.columns[0]
            first_col_lower = str(first_col).lower()
            # Agar birinchi ustun ism ustuni bo'lsa (raqam emas)
            if any(keyword in first_col_lower for keyword in ['talabgor', 'name', 'ism', 'student', 'participant', 'foydalanuvchi']):
                participant_column = first_col
                logger.info(f"✅ Talabgor ustuni aniqlandi va olib tashlanadi: {first_col}")

        # Talabgor ism-familiyalarini saqlab qolish
        person_names = None
        if participant_column:
            person_names = data[participant_column].tolist()
            logger.info(f"✅ {len(person_names)} ta talabgor ismlari saqlandi")
            response_data = data.drop(columns=[participant_column])
        else:
            response_data = data

        # Convert all columns to numeric, handling errors
        numeric_data = response_data.copy()
        for col in numeric_data.columns:
            numeric_data[col] = pd.to_numeric(numeric_data[col], errors='coerce')

        # Remove any rows or columns that are all NaN after conversion
        numeric_data = numeric_data.dropna(how='all', axis=0)
        numeric_data = numeric_data.dropna(how='all', axis=1)

        # Check if we have valid data
        if numeric_data.empty or numeric_data.shape[0] < 2 or numeric_data.shape[1] < 2:
            # Check if auto file cleaner is enabled
            user_id = message.chat.id
            user_data = user_data_manager.get_user_data(user_id)
            auto_cleaner_enabled = user_data.get('auto_file_cleaner', False)

            if auto_cleaner_enabled:
                # AUTO CLEAN MODE: Automatically clean the file and retry analysis
                await message.reply_text(
                    "🧽 Auto File Cleaner: Fayl tozalanmoqda va tahlil qilinmoqda..."
                )

                try:
                    # Read original file again
                    if file_extension == '.csv':
                        try:
                            original_data = pd.read_csv(file_path)
                        except Exception:
                            original_data = pd.read_csv(file_path, encoding='latin-1')
                    else:
                        original_data = pd.read_excel(file_path)

                    # Clean the file using DataCleaner
                    cleaner = DataCleaner()
                    cleaned_data, metadata = cleaner.clean_data(original_data)

                    # Save cleaned file temporarily
                    upload_dir = "data/uploads"
                    os.makedirs(upload_dir, exist_ok=True)
                    cleaned_file_path = os.path.join(upload_dir, f"auto_cleaned_{user_id}_{context.user_data.get('pending_analysis_filename', 'file')}")

                    if file_extension == '.csv':
                        cleaned_data.to_csv(cleaned_file_path, index=False)
                    else:
                        cleaned_data.to_excel(cleaned_file_path, index=False, engine='openpyxl')

                    # Now use cleaned data for analysis
                    # Remove participant column from cleaned data and save names
                    person_names = None
                    if len(cleaned_data.columns) > 0:
                        first_col = cleaned_data.columns[0]
                        first_col_lower = str(first_col).lower()
                        if any(keyword in first_col_lower for keyword in ['talabgor', 'name', 'ism', 'student', 'participant']):
                            person_names = cleaned_data[first_col].tolist()
                            logger.info(f"✅ {len(person_names)} ta talabgor ismlari saqlandi")
                            cleaned_data = cleaned_data.drop(columns=[first_col])
                            logger.info(f"✅ Tozalangan fayldan talabgor ustuni olib tashlandi: {first_col}")

                    # Convert to numeric
                    for col in cleaned_data.columns:
                        cleaned_data[col] = pd.to_numeric(cleaned_data[col], errors='coerce')

                    cleaned_data = cleaned_data.dropna(how='all', axis=0)
                    cleaned_data = cleaned_data.dropna(how='all', axis=1)

                    # Update file_path to cleaned version
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    file_path = cleaned_file_path
                    data = cleaned_data
                    numeric_data = cleaned_data

                    # Check again
                    if numeric_data.empty or numeric_data.shape[0] < 2 or numeric_data.shape[1] < 2:
                        await message.reply_text(
                            "❌ Tozalashdan keyin ham ma'lumotlar yetarli emas!\n\n"
                            "Iltimos, faylingizni tekshiring va qayta yuboring."
                        )
                        if os.path.exists(cleaned_file_path):
                            os.remove(cleaned_file_path)
                        return

                    # Continue with analysis (don't return, let it flow to analyzer below)
                    await message.reply_text("✅ Fayl muvaffaqiyatli tozalandi! Rasch tahlili boshlanmoqda...")

                except Exception as clean_error:
                    logger.error(f"Auto clean error: {clean_error}")
                    await message.reply_text(
                        f"❌ Avtomatik tozalashda xatolik: {str(clean_error)}\n\n"
                        "Iltimos, faylni qo'lda tozalang: ⚙️ Sozlamalar → 🧹 File Analyzer"
                    )
                    return
            else:
                # AUTO CLEANER DISABLED: Show error with manual clean option
                keyboard = [
                    [InlineKeyboardButton("🧹 Faylni avtomatik tozalash", callback_data='auto_clean_file')],
                    [InlineKeyboardButton("❌ Bekor qilish", callback_data='cancel_clean')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await message.reply_text(
                    "❌ Ma'lumotlar formatida xatolik!\n\n"
                    "Faylingiz talabga javob bermayapti. Sabablari:\n"
                    "• Talabgor ismlari ustuni mavjud (faqat 0/1 ma'lumotlar kerak)\n"
                    "• Qo'shimcha metadata ustunlar bor\n"
                    "• Bo'sh yoki noto'g'ri formatdagi ustunlar\n\n"
                    "✅ Yechim: File Analyzer orqali avtomatik tozalash\n\n"
                    "💡 Maslahat: Auto File Cleaner'ni yoqing (⚙️ Sozlamalar → 🧽 Auto File Cleaner)",
                    reply_markup=reply_markup
                )

                # Save file path for auto-clean
                context.user_data['pending_clean_file'] = file_path
                context.user_data['pending_clean_filename'] = context.user_data.get('pending_analysis_filename', 'file')
                return

        # Initialize status message for progress updates
        status_message = await message.reply_text("⏳ Tahlil qilinmoqda...\n\n▰▱▱▱▱▱▱▱▱▱ 10%\n_Ma'lumotlar o'qilmoqda..._", parse_mode='Markdown')

        try:
            analyzer = RaschAnalyzer()
            results = analyzer.fit(numeric_data, person_names=person_names)
        except Exception as analysis_error:
            # If analyzer.fit() fails, check if auto cleaner is enabled
            user_id = message.chat.id
            user_data = user_data_manager.get_user_data(user_id)
            auto_cleaner_enabled = user_data.get('auto_file_cleaner', False)

            if auto_cleaner_enabled:
                # AUTO CLEAN MODE: Automatically clean the file and retry analysis
                await status_message.edit_text("🧽 Auto File Cleaner: Fayl tozalanmoqda...", parse_mode='Markdown')

                try:
                    # Read original file again
                    if file_extension == '.csv':
                        try:
                            original_data = pd.read_csv(file_path)
                        except Exception:
                            original_data = pd.read_csv(file_path, encoding='latin-1')
                    else:
                        original_data = pd.read_excel(file_path)

                    # Clean the file using DataCleaner
                    cleaner = DataCleaner()
                    cleaned_data, metadata = cleaner.clean_data(original_data)

                    # Now use cleaned data for analysis
                    # Remove participant column from cleaned data and save names
                    person_names = None
                    if len(cleaned_data.columns) > 0:
                        first_col = cleaned_data.columns[0]
                        first_col_lower = str(first_col).lower()
                        if any(keyword in first_col_lower for keyword in ['talabgor', 'name', 'ism', 'student', 'participant']):
                            person_names = cleaned_data[first_col].tolist()
                            logger.info(f"✅ {len(person_names)} ta talabgor ismlari saqlandi")
                            cleaned_data = cleaned_data.drop(columns=[first_col])
                            logger.info(f"✅ Tozalangan fayldan talabgor ustuni olib tashlandi: {first_col}")

                    # Convert to numeric
                    for col in cleaned_data.columns:
                        cleaned_data[col] = pd.to_numeric(cleaned_data[col], errors='coerce')

                    cleaned_data = cleaned_data.dropna(how='all', axis=0)
                    cleaned_data = cleaned_data.dropna(how='all', axis=1)

                    # Update numeric_data to cleaned version
                    numeric_data = cleaned_data

                    # Retry analysis with cleaned data
                    await status_message.edit_text("⏳ Tahlil qilinmoqda...\n\n▰▰▰▱▱▱▱▱▱▱ 40%\n_Tozalangan fayl tahlil qilinmoqda..._", parse_mode='Markdown')

                    analyzer = RaschAnalyzer()
                    results = analyzer.fit(numeric_data, person_names=person_names)

                except Exception as clean_error:
                    logger.error(f"Auto clean error after analyzer failure: {clean_error}")
                    await status_message.delete()
                    await message.reply_text(
                        f"❌ Avtomatik tozalashda xatolik: {str(clean_error)}\n\n"
                        "Iltimos, faylni qo'lda tozalang: ⚙️ Sozlamalar → 🧹 File Analyzer"
                    )
                    return
            else:
                # Auto cleaner disabled, show error
                await status_message.delete()
                raise analysis_error

        # Update status message to 50%
        await status_message.edit_text("📊 *Tahlil qilinmoqda...*\n\n▰▰▰▱▱▱▱▱▱▱ 50%\n_Natijalar hisoblanmoqda..._", parse_mode='Markdown')

        summary_text = analyzer.get_summary(results)

        pdf_generator = PDFReportGenerator()

        # Generate general statistics report
        general_pdf_path = pdf_generator.generate_report(
            results,
            filename="statistika"
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
            context.user_data['status_message'] = status_message # Pass status message for updates

            # Start section configuration
            sections = get_sections(selected_subject)
            context.user_data['configuring_sections'] = True
            context.user_data['current_subject'] = selected_subject
            context.user_data['sections_list'] = sections
            context.user_data['current_section_index'] = 0
            context.user_data['section_questions'] = {}

            # Update status message to 95%
            await status_message.edit_text("📊 *Tahlil qilinmoqda...*\n\n▰▰▰▰▰▰▰▰▰▰ 95%\n_Yakunlanmoqda..._", parse_mode='Markdown')

            await message.reply_text(
                f"📋 *{selected_subject}* fani uchun bo'limlar bo'yicha savol raqamlarini kiritish:\n\n"
                f"Jami {len(sections)} ta bo'lim mavjud.\n\n"
                f"*1-bo'lim: {sections[0]}*\n\n"
                f"Ushbu bo'limga tegishli savol raqamlarini kiriting.\n"
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

        # Update status message to 95% if not configuring sections
        await status_message.edit_text("📊 *Tahlil qilinmoqda...*\n\n▰▰▰▰▰▰▰▰▰▰ 95%\n_Yakunlanmoqda..._", parse_mode='Markdown')

        # Generate person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename="talabgorlar-statistikasi",
            section_questions=section_questions if section_results_enabled else None
        )

        # Update status message to 100%
        await status_message.edit_text("✅ *Tahlil yakunlandi!*\n\n▰▰▰▰▰▰▰▰▰▰ 100%\n_Natijalar yuborilmoqda..._", parse_mode='Markdown')

        # Send quick summary before sending PDFs
        person_stats = results.get('person_statistics', {})
        individual_data = person_stats.get('individual', [])

        if individual_data:
            n_persons = len(individual_data)

            # Calculate statistics
            scores = [p['raw_score'] for p in individual_data if not np.isnan(p['raw_score'])]
            t_scores = [p['t_score'] for p in individual_data if not np.isnan(p['t_score'])]

            if scores and t_scores:
                avg_score = sum(scores) / len(scores)
                max_score_val = max(scores)
                min_score_val = min(scores)
                avg_t_score = sum(t_scores) / len(t_scores)

                # Calculate percentages based on T-scores
                percentages = [(t/65)*100 for t in t_scores]
                # Cap percentages
                percentages = [min(100, max(0 if p < 70 else p, p)) for p in percentages]
                avg_percentage = sum(percentages) / len(percentages)

                # Grade distribution
                grade_counts = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C+': 0, 'C': 0, 'NC': 0}
                for t in t_scores:
                    if t >= 70:
                        grade_counts['A+'] += 1
                    elif t >= 65:
                        grade_counts['A'] += 1
                    elif t >= 60:
                        grade_counts['B+'] += 1
                    elif t >= 55:
                        grade_counts['B'] += 1
                    elif t >= 50:
                        grade_counts['C+'] += 1
                    elif t >= 46:
                        grade_counts['C'] += 1
                    else:
                        grade_counts['NC'] += 1

                # Create summary message
                summary_text = (
                    f"📊 *Tahlil Natijalari - Qisqacha*\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👥 *Umumiy ma'lumot:*\n"
                    f"  • Talabgorlar: {n_persons} ta\n"
                    f"  • Savollar: {results.get('n_items', 0)} ta\n"
                    f"  • Ishonchlilik: {results.get('reliability', 0):.3f}\n\n"
                    f"📈 *Ball ko'rsatkichlari:*\n"
                    f"  • O'rtacha ball: {avg_score:.1f}/{results.get('n_items', 0)}\n"
                    f"  • Eng yuqori: {max_score_val}\n"
                    f"  • Eng past: {min_score_val}\n\n"
                    f"🎯 *T-Score va Foiz:*\n"
                    f"  • O'rtacha T-Score: {avg_t_score:.1f}\n"
                    f"  • O'rtacha natija: {avg_percentage:.1f}%\n\n"
                    f"🏆 *Darajalar taqsimoti:*\n"
                )

                for grade, count in grade_counts.items():
                    if count > 0:
                        percentage = (count / n_persons) * 100
                        summary_text += f"  • {grade}: {count} ta ({percentage:.1f}%)\n"

                summary_text += "\n━━━━━━━━━━━━━━━━━━━━\n"
            else:
                summary_text = f"📊 *Tahlil Natijalari - Qisqacha*\n\n"
            summary_text += "📄 Batafsil natijalar PDF faylda yuborilmoqda..."

            await message.reply_text(summary_text, parse_mode='Markdown')

        # Send general statistics PDF
        if general_pdf_path and os.path.exists(general_pdf_path):
            with open(general_pdf_path, 'rb') as pdf_file:
                await message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(general_pdf_path),
                    caption="📊 Umumiy statistika va item parametrlari"
                )

        # Send person results PDF
        with open(person_pdf_path, 'rb') as pdf_file:
            await message.reply_document(
                document=pdf_file,
                filename=os.path.basename(person_pdf_path),
                caption="👥 Talabgorlar natijalari (Umumiy)"
            )

        # Generate and send section results if enabled and configured
        if section_results_enabled and section_questions:
            section_pdf_path = pdf_generator.generate_section_results_report(
                results,
                filename="bulimlar-statistikasi",
                section_questions=section_questions
            )

            with open(section_pdf_path, 'rb') as pdf_file:
                await message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(section_pdf_path),
                    caption="📋 Bo'limlar bo'yicha natijalar (T-Score)"
                )

        await message.reply_text(
            "✅ Barcha hisobotlar yuborildi!",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

        # # AI Analysis
        # try:
        #     ai_analyzer = AIAnalyzer()
        #     if ai_analyzer.is_available():
        #         await message.reply_text(
        #             "🤖 AI natijalarni tahlil qilmoqda...",
        #             parse_mode='Markdown'
        #         )

        #         ai_opinion = ai_analyzer.analyze_test_results(results)

        #         await message.reply_text(
        #             f"🤖 *AI Fikri*\n"
        #             f"━━━━━━━━━━━━━━━━━━━━\n\n"
        #             f"{ai_opinion}",
        #             parse_mode='Markdown'
        #         )
        #     else:
        #         logger.info("AI analyzer not available (API key not set)")
        #         await message.reply_text(
        #             "ℹ️ AI tahlili hozirda mavjud emas (API kalit sozlanmagan)",
        #             parse_mode='Markdown'
        #         )
        # except Exception as ai_error:
        #     logger.warning(f"AI analysis failed: {str(ai_error)}")
        #     await message.reply_text(
        #         "ℹ️ AI tahlili amalga oshmadi",
        #         parse_mode='Markdown'
        #     )

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

        # Clear pending data
        context.user_data.pop('pending_analysis_file', None)
        context.user_data.pop('pending_analysis_filename', None)
        context.user_data.pop('pending_file_extension', None)
        context.user_data.pop('pending_payment_file', None)

        logger.info(f"Successfully processed file for user {user_id}")

    except pd.errors.EmptyDataError:
        await message.reply_text(
            "❌ Fayl bo'sh yoki noto'g'ri formatda!\n\n"
            "Iltimos, to'g'ri ma'lumotlar bilan qayta urinib ko'ring."
        )
    except Exception as e:
        logger.error(f"Error processing file for user {user_id}: {str(e)}")
        error_message = str(e).lower()

        # Check if error is related to data format issues
        if any(keyword in error_message for keyword in ['string', 'text', 'object', 'cannot convert', 'invalid literal']):
            await message.reply_text(
                f"❌ Ma'lumot formati noto'g'ri!\n\n"
                f"Sabab: Faylda matn yoki noto'g'ri formatdagi ma'lumotlar mavjud.\n\n"
                f"💡 Yechim:\n"
                f"1. 'Boshqa' menyusidan 'File Analyzer' ni tanlang\n"
                f"2. 'To'liq tozalash' yoki 'Faqat standartlashtirish' ni tanlang\n"
                f"3. Faylni qayta yuboring\n\n"
                f"File Analyzer faylingizni tahlil uchun tayyorlaydi."
            )
        else:
            await message.reply_text(
                f"❌ Xatolik yuz berdi: {str(e)}\n\n"
                f"Iltimos, faylingizni tekshiring va qayta urinib ko'ring.\n\n"
                f"💡 Agar faylda ortiqcha ustunlar yoki qatorlar bo'lsa,\n"
                f"'Boshqa' → 'File Analyzer' orqali faylni tozalang.\n\n"
                f"Yordam: /help"
            )


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Profile button"""
    user = update.effective_user
    user_data = user_data_manager.get_user_data(user.id)

    # Get user statistics
    students = student_data_manager.get_all_students(user.id)
    students_count = len(students)

    user_tests = test_manager.get_teacher_tests(user.id)
    total_tests = len(user_tests)
    active_tests = sum(1 for test in user_tests if test.get('is_active', False))

    # Get payment history count
    payment_history = payment_manager.get_user_payments(user.id)
    total_analyses = len(payment_history)

    # Get user preferences
    section_results_enabled = user_data.get('section_results_enabled', False)
    auto_file_cleaner = user_data.get('auto_file_cleaner', False)

    # Display profile information with statistics
    profile_text = (
        f"👤 *Profil ma'lumotlari*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *Shaxsiy ma'lumotlar:*\n"
        f"  • Ism va Familiya: {user_data.get('full_name') or 'Kiritilmagan'}\n"
        f"  • Mutaxassislik: {user_data.get('subject') or 'Kiritilmagan'}\n"
        f"  • Bio: {user_data.get('bio') or 'Kiritilmagan'}\n"
        f"  • Telefon: {user_data.get('phone') or 'Kiritilmagan'}\n"
        f"  • Tajriba: {user_data.get('experience_years') or 'Kiritilmagan'}\n"
        f"  • Telegram: @{user.username or 'N/A'}\n"
        f"  • ID: `{user.id}`\n\n"
        f"📊 *Statistika:*\n"
        f"  • O'quvchilar: {students_count} ta\n"
        f"  • Testlar: {total_tests} ta (faol: {active_tests})\n"
        f"  • Tahlillar: {total_analyses} ta\n\n"
        f"⚙️ *Sozlamalar:*\n"
        f"  • Bo'limlar bo'yicha natijalash: {'✅' if section_results_enabled else '❌'}\n"
        f"  • Auto File Cleaner: {'✅' if auto_file_cleaner else '❌'}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Ma'lumotlarni tahrirlash uchun quyidagi tugmalardan foydalaning:"
    )

    # Inline keyboard for editing
    keyboard = [
        [InlineKeyboardButton("✏️ Ism va Familiya", callback_data='edit_full_name')],
        [InlineKeyboardButton("✏️ Bio", callback_data='edit_bio')],
        [InlineKeyboardButton("📸 Foto", callback_data='edit_photo'),
         InlineKeyboardButton("📞 Telefon", callback_data='edit_phone')],
        [InlineKeyboardButton("📅 Tajriba yili", callback_data='edit_experience')],
        [InlineKeyboardButton("📊 Batafsil statistika", callback_data='view_detailed_stats')],
        [InlineKeyboardButton("📤 Ulashish", callback_data='share_profile')]
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

    elif query.data == 'edit_phone':
        context.user_data['editing'] = 16  # WAITING_FOR_PHONE
        await query.message.reply_text(
            "📞 Telefon raqamingizni kiriting:\n"
            "(masalan: +998901234567)",
            reply_markup=get_main_keyboard()
        )

    elif query.data == 'edit_experience':
        context.user_data['editing'] = 17  # WAITING_FOR_EXPERIENCE
        await query.message.reply_text(
            "📅 Tajriba yilingizni kiriting:\n"
            "(masalan: 5 yil yoki 2019 yildan)",
            reply_markup=get_main_keyboard()
        )

    elif query.data == 'edit_photo':
        context.user_data['editing'] = 18  # WAITING_FOR_PHOTO
        await query.message.reply_text(
            "📸 Profilingiz uchun rasm yuboring:",
            reply_markup=get_main_keyboard()
        )

    elif query.data == 'share_profile':
        user_id = update.effective_user.id
        user = update.effective_user
        user_data = user_data_manager.get_user_data(user_id)

        # Chiroyli formatlangan profil ma'lumotlari
        full_name = user_data.get('full_name') or "O'qituvchi"
        share_text = (
            f"👤 *{full_name}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📚 *Mutaxassislik:* {user_data.get('subject') or 'Belgilanmagan'}\n"
        )

        if user_data.get('experience_years'):
            share_text += f"📅 *Tajriba:* {user_data.get('experience_years')}\n"

        if user_data.get('phone'):
            share_text += f"📞 *Telefon:* {user_data.get('phone')}\n"

        if user.username:
            share_text += f"📱 *Telegram:* @{user.username}\n"

        share_text += f"\n"

        if user_data.get('bio'):
            share_text += f"📝 *Haqimda:*\n{user_data.get('bio')}\n\n"

        # Statistika
        students = student_data_manager.get_all_students(user_id)
        user_tests = test_manager.get_teacher_tests(user_id)

        share_text += (
            f"📊 *Statistika:*\n"
            f"  • O'quvchilar: {len(students)} ta\n"
            f"  • Testlar: {len(user_tests)} ta\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 @RaschAnalyzerBot orqali"
        )

        # Agar foto mavjud bo'lsa, foto bilan yuboring
        photo_id = user_data.get('profile_photo_id')
        if photo_id:
            try:
                await query.message.reply_photo(
                    photo=photo_id,
                    caption=share_text,
                    parse_mode='Markdown'
                )
            except Exception:
                await query.message.reply_text(share_text, parse_mode='Markdown')
        else:
            await query.message.reply_text(share_text, parse_mode='Markdown')

        await query.answer("✅ Profil ma'lumotlari tayyor!")

    # Handle time restriction choice for test creation
    elif query.data == 'time_restriction_yes':
        context.user_data['creating_test'] = WAITING_FOR_TEST_START_DATE
        await query.message.reply_text(
            "📅 Test boshlanish sanasini kiriting\n"
            "(Format: KK.OO.YYYY, masalan: 25.10.2025):"
        )

    elif query.data == 'time_restriction_no':
        # Set test without time restrictions, then ask about payment
        test_temp = context.user_data.get('test_temp', {})
        test_temp['start_date'] = ''
        test_temp['start_time'] = ''
        test_temp['duration'] = 60  # Default duration
        context.user_data['test_temp'] = test_temp
        context.user_data['creating_test'] = WAITING_FOR_PAID_TEST_CHOICE

        # Ask if test should be paid
        keyboard = [
            [
                InlineKeyboardButton("💰 Pullik", callback_data="paid_test_yes"),
                InlineKeyboardButton("🆓 Tekin", callback_data="paid_test_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            "💵 *Testni pullik qilasizmi?*\n\n"
            "• *Pullik* - Talabalar test ishlash uchun to'lov qiladi (10-100 ⭐)\n"
            "  Siz daromadning 80% ni olasiz\n\n"
            "• *Tekin* - Talabalar bepul test ishlaydi",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # Handle question upload method choice - Only PDF allowed for tests
    elif query.data == 'upload_questions_file':
        context.user_data['creating_test'] = WAITING_FOR_PDF_QUESTION_FILE
        await query.message.reply_text(
            "📄 Test savollarini o'z ichiga olgan PDF faylni yuboring.\n\n"
            "PDF yuklangandan so'ng, testda nechta savol borligini so'raymiz.\n"
            "Keyin har bir savol uchun to'g'ri javobni tanlaysiz."
        )

    elif query.data == 'upload_excel_questions':
        # Excel is only for sample analysis, not for creating tests
        await query.message.reply_text(
            "❌ Excel faqat namuna tahlil uchun ishlatiladi.\n\n"
            "Test yaratish uchun PDF fayl yuklashingiz kerak.\n\n"
            "Bosh menyuga qaytish uchun /start buyrug'ini yuboring."
        )

    elif query.data == 'add_questions_manually':
        context.user_data['creating_test'] = WAITING_FOR_QUESTION_TEXT
        await query.message.reply_text(
            "✍️ Birinchi savol matnini kiriting:"
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

    # Handle paid test choice callbacks
    elif query.data == 'paid_test_yes':
        await query.answer()
        context.user_data['creating_test'] = WAITING_FOR_TEST_PRICE
        await query.message.reply_text(
            "💰 *Test narxini belgilang*\n\n"
            "10 dan 100 gacha Stars miqdorida narx kiriting.\n\n"
            "Masalan: 50\n\n"
            "💡 Talabalar to'lagan miqdorning 80% sizga,\n"
            "20% platformaga o'tadi.",
            parse_mode='Markdown'
        )

    elif query.data == 'paid_test_no':
        await query.answer()
        # Create free test
        user_id = update.effective_user.id
        test_temp = context.user_data.get('test_temp', {})
        test_temp['is_paid'] = False
        test_temp['price'] = 0

        test_id = test_manager.create_test(user_id, test_temp)
        context.user_data['current_test_id'] = test_id

        # Offer choice: upload file or add manually
        keyboard = [
            [InlineKeyboardButton("📁 Fayl orqali yuklash", callback_data="upload_questions_file")],
            [InlineKeyboardButton("✍️ Qo'lda qo'shish", callback_data="add_questions_manually")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        price_info = ""
        date_info = f"📅 Boshlanish: {test_temp['start_date']} {test_temp['start_time']}\n⏱ Davomiylik: {test_temp['duration']} daqiqa\n" if test_temp.get('start_date') else "⏱ Vaqt chegarasi: Yo'q\n"

        await query.message.reply_text(
            f"✅ Test muvaffaqiyatli yaratildi!\n\n"
            f"📋 *{test_temp['name']}*\n"
            f"📚 Fan: {test_temp['subject']}\n"
            f"{date_info}"
            f"🆓 Test: Tekin\n\n"
            "❓ Savollarni qanday qo'shmoqchisiz?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        context.user_data['creating_test'] = None

    # Handle test management callbacks
    elif query.data.startswith('activate_test_'):
        test_id = query.data.replace('activate_test_', '')
        if test_manager.activate_test(test_id):
            # Get student bot username from environment
            student_bot_username = os.getenv('STUDENT_BOT_USERNAME', 'Talabgor_bot')
            
            await query.edit_message_text(
                f"✅ Test faollashtirildi!\n\n"
                f"📱 *Talabgorlar uchun test havolasi:*\n"
                f"`https://t.me/{student_bot_username}?start=test_{test_id}`\n\n"
                f"Havolani talabgorlarga ulashing.",
                parse_mode='Markdown'
            )
        else:
            await query.answer("❌ Xatolik yuz berdi!")

    elif query.data.startswith('deactivate_test_'):
        test_id = query.data.replace('deactivate_test_', '')
        if test_manager.deactivate_test(test_id):
            await query.edit_message_text("⏸ Test faolsizlantirildi!")
        else:
            await query.answer("❌ Xatolik yuz berdi!")

    elif query.data.startswith('delete_test_'):
        test_id = query.data.replace('delete_test_', '')
        if test_manager.delete_test(test_id, user_id):
            await query.edit_message_text("🗑 Test o'chirildi!")
        else:
            await query.answer("❌ Xatolik yuz berdi!")

    # Handle correct answer selection from uploaded questions
    elif query.data.startswith('set_correct_'):
        parts = query.data.split('_')
        question_index = int(parts[2])
        answer_index = int(parts[3])

        questions = context.user_data.get('uploaded_questions', [])
        if question_index < len(questions):
            question = questions[question_index]

            # Add question to test
            test_id = context.user_data['current_test_id']
            question_data = {
                'text': question['text'],
                'options': question['options'],
                'correct_answer': answer_index,
                'points': 1
            }
            test_manager.add_question(test_id, question_data)

            await query.answer(f"✅ To'g'ri javob: {chr(65 + answer_index)}")

            # Move to next question
            context.user_data['current_question_index_for_answer'] = question_index + 1

            # Create a temporary Update-like object to pass message context
            class MessageWrapper:
                def __init__(self, msg):
                    self.message = msg

            # Show next question using the message from callback
            await show_question_for_correct_answer(MessageWrapper(query.message), context)

    # Handle PDF question correct answer selection
    elif query.data.startswith('pdf_correct_'):
        parts = query.data.split('_')
        question_index = int(parts[2])
        answer_index = int(parts[3])

        pdf_questions = context.user_data.get('pdf_questions', [])
        if question_index < len(pdf_questions):
            # Set correct answer
            pdf_questions[question_index]['correct_answer'] = answer_index

            selected_option = pdf_questions[question_index]['options'][answer_index]
            await query.answer(f"✅ To'g'ri javob: {selected_option}")

            # Move to next question
            context.user_data['current_pdf_question_index'] = question_index + 1

            # Show next question - pass message directly
            await show_pdf_question_answer_selector(query.message, context)

    # Handle adding more options to PDF question
    elif query.data.startswith('add_pdf_option_'):
        parts = query.data.split('_')
        question_index = int(parts[3])

        pdf_questions = context.user_data.get('pdf_questions', [])
        if question_index < len(pdf_questions):
            question = pdf_questions[question_index]

            # Add next letter option (E, F, G, etc.)
            next_letter = chr(65 + len(question['options']))
            question['options'].append(next_letter)

            await query.answer(f"➕ Variant qo'shildi: {next_letter}")

            # Refresh the keyboard with new option - pass message directly
            await show_pdf_question_answer_selector(query.message, context)

    elif query.data.startswith('test_results_'):
        test_id = query.data.replace('test_results_', '')
        test = test_manager.get_test(test_id)

        if test:
            is_finalized = test.get('finalized_at') is not None
            has_time_limit = test.get('start_date') and test.get('start_time')

            # Check if results have been sent to students
            from bot.database.managers import TestResultManager
            results_sent = await TestResultManager.check_results_sent(test_id)

            participants = test.get('participants', {})

            # Qisqacha statistika hisoblash
            total_participants = 0
            completed_tests_finalized = 0 # Count finalized tests for summary
            if isinstance(participants, dict):
                total_participants = len(participants)
            elif isinstance(participants, list):
                total_participants = len(participants)

            if is_finalized:
                completed_tests_finalized = 1

            if total_participants > 0:
                scores = []
                percentages = []

                # Handle both dict and list formats
                participant_list = participants.values() if isinstance(participants, dict) else participants

                for p in participant_list:
                    if isinstance(p, dict):
                        scores.append(p.get('score', 0))
                        percentages.append(p.get('percentage', 0))

                if scores:
                    avg_score = sum(scores) / len(scores)
                    max_score_val = max(scores)
                    min_score_val = min(scores)
                    avg_percentage = sum(percentages) / len(percentages)

                    # Darajalar statistikasi
                    grade_counts = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C+': 0, 'C': 0, 'NC': 0}
                    for perc in percentages:
                        if perc >= 90:
                            grade_counts['A+'] += 1
                        elif perc >= 80:
                            grade_counts['A'] += 1
                        elif perc >= 70:
                            grade_counts['B+'] += 1
                        elif perc >= 60:
                            grade_counts['B'] += 1
                        elif perc >= 50:
                            grade_counts['C+'] += 1
                        elif perc >= 40:
                            grade_counts['C'] += 1
                        else:
                            grade_counts['NC'] += 1

                    # Qisqacha xabar
                    summary_text = (
                        f"📊 *{test['name']}*\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👥 *Umumiy ma'lumot:*\n"
                        f"  • Ishtirokchilar: {total_participants} ta\n"
                        f"  • O'rtacha ball: {avg_score:.1f}/{test.get('questions', [{}])[0].get('points', 1) * len(test.get('questions', []))}\n"
                        f"  • O'rtacha natija: {avg_percentage:.1f}%\n\n"
                        f"📈 *Ballar:*\n"
                        f"  • Eng yuqori: {max_score_val}\n"
                        f"  • Eng past: {min_score_val}\n\n"
                        f"🎯 *Darajalar taqsimoti:*\n"
                    )

                    for grade, count in grade_counts.items():
                        if count > 0:
                            summary_text += f"  • {grade}: {count} ta\n"

                    summary_text += "\n━━━━━━━━━━━━━━━━━━━━\n"
                else:
                    summary_text = f"📊 *{test['name']}*\n\nIshtirokchilar: {total_participants} ta\n\n"
            else:
                summary_text = f"📊 *{test['name']}*\n\nHali ishtirokchilar yo'q.\n\n"

            results_text = summary_text + "\n*📋 Batafsil natijalar:*\n\n"

            if participants:
                # Handle both dict and list formats
                if isinstance(participants, dict):
                    for user_id_str, p in participants.items():
                        if isinstance(p, dict):
                            results_text += (
                                f"👤 Talabgor {p.get('student_id', user_id_str)}\n"
                                f"   Ball: {p.get('score', 0)}/{p.get('max_score', 0)}\n"
                                f"   Foiz: {p.get('percentage', 0):.1f}%\n\n"
                            )
                elif isinstance(participants, list):
                    for p in participants:
                        if isinstance(p, dict):
                            results_text += (
                                f"👤 Talabgor {p.get('student_id', 'N/A')}\n"
                                f"   Ball: {p.get('score', 0)}/{p.get('max_score', 0)}\n"
                                f"   Foiz: {p.get('percentage', 0):.1f}%\n\n"
                            )

                # Build keyboard based on test state
                keyboard = []

                if not is_finalized:
                    # For tests without time limit - show finalize and show results button
                    if not has_time_limit:
                        keyboard.append([InlineKeyboardButton("📊 Natijalarni ko'rsatish", callback_data=f"manual_finalize_{test_id}")])
                        keyboard.append([InlineKeyboardButton("🔚 Testni yakunlash (natijalar yuborilmaydi)", callback_data=f"finalize_test_{test_id}")])
                    else:
                        # For time-limited tests - show analysis and finalize buttons
                        keyboard.append([InlineKeyboardButton("📈 Rasch tahlili", callback_data=f"rasch_analysis_{test_id}")])
                        keyboard.append([InlineKeyboardButton("🔚 Testni yakunlash", callback_data=f"finalize_test_{test_id}")])
                else:
                    # Test already finalized - show re-analysis option
                    keyboard.append([InlineKeyboardButton("🔄 Rasch tahlilini qayta amalga oshirish", callback_data=f"rasch_analysis_{test_id}")])

                    # Add "Send results" button only if results haven't been sent yet
                    if not results_sent:
                        keyboard.append([InlineKeyboardButton("📤 Talabgorlarga natijalarni yuborish", callback_data=f"send_results_{test_id}")])

                    # Add student bot link info
                    student_bot_username = os.getenv('STUDENT_BOT_USERNAME', 'Talabgor_bot')
                    results_text += f"\n\n📱 *Test havolasi (talabgorlar uchun):*\n`https://t.me/{student_bot_username}?start=test_{test_id}`"

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(results_text, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                results_text += "Hali natijalar yo'q."
                await query.edit_message_text(results_text, parse_mode='Markdown')
        else:
            await query.answer("❌ Test topilmadi!")

    elif query.data.startswith('rasch_analysis_'):
        test_id = query.data.replace('rasch_analysis_', '')
        await query.answer("⏳ Rasch tahlili boshlanmoqda...")

        await perform_test_rasch_analysis(query.message, context, test_id)

    elif query.data.startswith('send_results_'):
        test_id = query.data.replace('send_results_', '')

        # Check if results have already been sent
        from bot.database.managers import TestResultManager
        results_sent = await TestResultManager.check_results_sent(test_id)

        if results_sent:
            await query.answer("✅ Natijalar allaqachon yuborilgan!", show_alert=True)
            return

        await query.answer("⏳ Talabgorlarga natijalar yuborilmoqda...")

        # Import the function to send results
        from bot.utils.test_scheduler import send_test_results_to_students

        try:
            # Get student bot application from bot_data
            student_bot_app = context.application.bot_data.get('student_bot_app')

            if not student_bot_app:
                await query.edit_message_text(
                    "❌ Student bot topilmadi!\n\n"
                    "Natijalarni yuborish uchun student bot ishlab turishi kerak."
                )
                return

            # Send results to all students
            result = await send_test_results_to_students(test_id, student_bot_app)

            if result.get('success'):
                count = result.get('count', 0)
                if result.get('already_sent'):
                    await query.edit_message_text(
                        "ℹ️ Barcha talabgorlarga natijalar allaqachon yuborilgan!"
                    )
                else:
                    await query.edit_message_text(
                        f"✅ Natijalar muvaffaqiyatli yuborildi!\n\n"
                        f"📤 {count} ta talabgorga natijalar yuborildi.\n\n"
                        f"Talabgorlar o'z natijalarini telegram orqali ko'rishlari mumkin."
                    )
            else:
                error_msg = result.get('error', 'Noma\'lum xatolik')
                await query.edit_message_text(
                    f"❌ Natijalarni yuborishda xatolik yuz berdi!\n\n"
                    f"Xatolik: {error_msg}"
                )
        except Exception as e:
            logger.error(f"Send results error: {e}")
            await query.edit_message_text(
                f"❌ Natijalarni yuborishda xatolik yuz berdi!\n\n"
                f"Xatolik: {str(e)}"
            )

    elif query.data.startswith('manual_finalize_'):
        # Manual finalize - finalize test and automatically run Rasch analysis
        test_id = query.data.replace('manual_finalize_', '')

        await query.answer("⏳ Test yakunlanmoqda va tahlil qilinmoqda...")

        # Import process_and_send_test_results
        from bot.utils.test_scheduler import process_and_send_test_results

        try:
            # Get student bot application from bot_data
            student_bot_app = context.application.bot_data.get('student_bot_app')
            await process_and_send_test_results(context.application, test_id, student_bot_app=student_bot_app)
            await query.edit_message_text(
                "✅ Test yakunlandi va natijalar yuborildi!\n\n"
                "Rasch tahlili PDF fayllarini yuqorida ko'rishingiz mumkin.\n"
                "Talabgorlarga sertifikatlar yuborildi."
            )
        except Exception as e:
            logger.error(f"Manual finalize error: {e}")
            await query.edit_message_text(
                "❌ Test yakunlashda yoki tahlil qilishda xatolik yuz berdi!\n\n"
                f"Xatolik: {str(e)}"
            )

    elif query.data.startswith('finalize_test_'):
        test_id = query.data.replace('finalize_test_', '')

        if test_manager.finalize_test(test_id):
            await query.edit_message_text(
                "✅ Test yakunlandi!\n\n"
                "Test endi yangi ishtirokchilarni qabul qilmaydi.\n"
                "Rasch tahlili uchun test natijalarini ko'ring."
            )
        else:
            await query.answer("❌ Xatolik yuz berdi!")

    elif query.data.startswith('share_test_'):
        test_id = query.data.replace('share_test_', '')
        test = test_manager.get_test(test_id)

        if test:
            # Get student bot username from environment
            student_bot_username = os.getenv('STUDENT_BOT_USERNAME', 'Talabgor_bot')
            
            logger.info(f"Test ulashish: {test_id}, Student bot: {student_bot_username}")
            
            # Build time info
            start_date = test.get('start_date', '')
            start_time = test.get('start_time', '')
            
            if start_date and start_time:
                time_info = f"📅 Boshlanish: {start_date} {start_time}\n⏱ Davomiyligi: {test['duration']} daqiqa"
            else:
                time_info = f"⏱ Vaqt chegarasi: Yo'q (istalgan vaqtda topshirish mumkin)"

            # Create shareable message with inline button
            share_text = (
                f"📝 *{test['name']}*\n\n"
                f"📚 Fan: {test['subject']}\n"
                f"{time_info}\n"
                f"📝 Savollar: {len(test['questions'])} ta\n\n"
                f"Testni ishlash uchun pastdagi tugmani bosing 👇"
            )

            # Create inline button for test
            test_link = f"https://t.me/{student_bot_username}?start={test_id}"
            logger.info(f"Test havolasi: {test_link}")
            
            share_keyboard = [
                [InlineKeyboardButton("📝 Testni boshlash", url=test_link)]
            ]
            share_markup = InlineKeyboardMarkup(share_keyboard)

            # Send shareable message
            await query.message.reply_text(
                share_text,
                parse_mode='Markdown',
                reply_markup=share_markup
            )
            
            await query.answer("✅ Test ulashish xabari yuborildi! Uni kanalingizga yoki guruhingizga forward qilishingiz mumkin.")
        else:
            await query.answer("❌ Test topilmadi!")

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

    # Handle auto file analyzer toggle
    elif query.data == 'auto_analyzer_on':
        user_data_manager.update_user_field(user_id, 'auto_file_analyzer', True)

        analyzer_text = (
            f"🤖 *Auto File Analyzer*\n\n"
            f"Hozirgi holat: ✅ *Yoqilgan*\n\n"
            f"Bu funksiya fayl yuborilganda avtomatik:\n"
            f"• ✅ Yoqilgan: Fayl avtomatik tahlil qilinadi\n"
            f"• ❌ O'chirilgan: Fayl tahlil qilinmaydi (faqat saqlanadi)\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✔️ Yoqilgan", callback_data='auto_analyzer_on'),
                InlineKeyboardButton("❌ O'chirish", callback_data='auto_analyzer_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            analyzer_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("✅ Auto File Analyzer yoqildi!")

    elif query.data == 'auto_analyzer_off':
        user_data_manager.update_user_field(user_id, 'auto_file_analyzer', False)

        analyzer_text = (
            f"🤖 *Auto File Analyzer*\n\n"
            f"Hozirgi holat: ❌ *O'chirilgan*\n\n"
            f"Bu funksiya fayl yuborilganda avtomatik:\n"
            f"• ✅ Yoqilgan: Fayl avtomatik tahlil qilinadi\n"
            f"• ❌ O'chirilgan: Fayl tahlil qilinmaydi (faqat saqlanadi)\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Yoqish", callback_data='auto_analyzer_on'),
                InlineKeyboardButton("✖️ O'chirilgan", callback_data='auto_analyzer_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            analyzer_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("❌ Auto File Analyzer o'chirildi!")

    # Handle auto file cleaner toggle
    elif query.data == 'auto_cleaner_on':
        user_data_manager.update_user_field(user_id, 'auto_file_cleaner', True)

        cleaner_text = (
            f"🧽 *Auto File Cleaner*\n\n"
            f"Hozirgi holat: ✅ *Yoqilgan*\n\n"
            f"Bu funksiya tahlil qilayotganda:\n"
            f"• ✅ Yoqilgan: Talabga javob bermasa avtomatik tozalaydi\n"
            f"• ❌ O'chirilgan: Xato xabari chiqaradi\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✔️ Yoqilgan", callback_data='auto_cleaner_on'),
                InlineKeyboardButton("❌ O'chirish", callback_data='auto_cleaner_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            cleaner_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("✅ Auto File Cleaner yoqildi!")

    elif query.data == 'auto_cleaner_off':
        user_data_manager.update_user_field(user_id, 'auto_file_cleaner', False)

        cleaner_text = (
            f"🧽 *Auto File Cleaner*\n\n"
            f"Hozirgi holat: ❌ *O'chirilgan*\n\n"
            f"Bu funksiya tahlil qilayotganda:\n"
            f"• ✅ Yoqilgan: Talabga javob bermasa avtomatik tozalaydi\n"
            f"• ❌ O'chirilgan: Xato xabari chiqaradi\n\n"
            f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Yoqish", callback_data='auto_cleaner_on'),
                InlineKeyboardButton("✖️ O'chirilgan", callback_data='auto_cleaner_off')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            cleaner_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await query.answer("❌ Auto File Cleaner o'chirildi!")

    # Handle detailed statistics view
    elif query.data == 'view_detailed_stats':
        user_id = update.effective_user.id
        students = student_data_manager.get_all_students(user_id)
        user_tests = test_manager.get_teacher_tests(user_id)
        payment_history = payment_manager.get_user_payments(user_id)

        # Calculate detailed stats
        total_participants = 0
        completed_tests = 0
        for test in user_tests:
            participants = test.get('participants', {})
            total_participants += len(participants)
            if test.get('finalized_at'):
                completed_tests += 1

        stats_text = (
            f"📊 *Batafsil Statistika*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 *O'quvchilar:*\n"
            f"  • Jami: {len(students)} ta\n\n"
            f"📝 *Testlar:*\n"
            f"  • Yaratilgan: {len(user_tests)} ta\n"
            f"  • Faol: {sum(1 for t in user_tests if t.get('is_active', False))} ta\n"
            f"  • Yakunlangan: {completed_tests} ta\n"
            f"  • Jami ishtirokchilar: {total_participants} ta\n\n"
            f"📈 *Tahlillar:*\n"
            f"  • Amalga oshirilgan: {len(payment_history)} ta\n"
        )

        if user_tests:
            recent_test = user_tests[-1]
            stats_text += (
                f"\n📌 *Oxirgi faoliyat:*\n"
                f"  • Test: {recent_test['name']}\n"
                f"  • Sana: {recent_test['created_at'][:10]}\n"
            )

        await query.edit_message_text(stats_text, parse_mode='Markdown')

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
    status_message = context.user_data.get('status_message') # Get status message


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
            # Update status message before generating reports
            if status_message:
                await status_message.edit_text("📊 *Tahlil qilinmoqda...*\n\n▰▰▰▰▰▰▰▰▰▰ 95%\n_Yakunlanmoqda..._", parse_mode='Markdown')

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
                filename="bulimlar-statistikasi",
                section_questions=section_questions
            )

            # Update status message to 100%
            if status_message:
                await status_message.edit_text("✅ *Tahlil yakunlandi!*\n\n▰▰▰▰▰▰▰▰▰▰ 100%\n_Natijalar yuborilmoqda..._", parse_mode='Markdown')

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
        context.user_data['status_message'] = None # Clear status message

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

    elif editing_state == WAITING_FOR_PHONE:
        user_data_manager.update_user_field(user_id, 'phone', text)
        await update.message.reply_text(
            f"✅ Telefon raqam saqlandi: *{text}*",
            parse_mode='Markdown'
        )
        context.user_data['editing'] = None

    elif editing_state == WAITING_FOR_EXPERIENCE:
        user_data_manager.update_user_field(user_id, 'experience_years', text)
        await update.message.reply_text(
            f"✅ Tajriba yili saqlandi: *{text}*",
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
        [KeyboardButton("🧽 Auto File Cleaner")],
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


async def handle_auto_file_analyzer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Auto File Analyzer button"""
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)

    # Get current state (default is off)
    auto_analyzer_enabled = user_data.get('auto_file_analyzer', False)

    status_icon = "✅" if auto_analyzer_enabled else "❌"
    status_text = "Yoqilgan" if auto_analyzer_enabled else "O'chirilgan"

    analyzer_text = (
        f"🤖 *Auto File Analyzer*\n\n"
        f"Hozirgi holat: {status_icon} *{status_text}*\n\n"
        f"Bu funksiya fayl yuborilganda avtomatik:\n"
        f"• ✅ Yoqilgan: Fayl avtomatik tahlil qilinadi\n"
        f"• ❌ O'chirilgan: Fayl tahlil qilinmaydi (faqat saqlanadi)\n\n"
        f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
    )

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Yoqish" if not auto_analyzer_enabled else "✔️ Yoqilgan",
                callback_data='auto_analyzer_on'
            ),
            InlineKeyboardButton(
                "❌ O'chirish" if auto_analyzer_enabled else "✖️ O'chirilgan",
                callback_data='auto_analyzer_off'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        analyzer_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_auto_file_cleaner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Auto File Cleaner button"""
    user_id = update.effective_user.id
    user_data = user_data_manager.get_user_data(user_id)

    # Get current state (default is off)
    auto_cleaner_enabled = user_data.get('auto_file_cleaner', False)

    status_icon = "✅" if auto_cleaner_enabled else "❌"
    status_text = "Yoqilgan" if auto_cleaner_enabled else "O'chirilgan"

    cleaner_text = (
        f"🧽 *Auto File Cleaner*\n\n"
        f"Hozirgi holat: {status_icon} *{status_text}*\n\n"
        f"Bu funksiya tahlil qilayotganda:\n"
        f"• ✅ Yoqilgan: Talabga javob bermasa avtomatik tozalaydi\n"
        f"• ❌ O'chirilgan: Xato xabari chiqaradi\n\n"
        f"Funksiyani yoqish yoki o'chirish uchun quyidagi tugmalardan birini tanlang:"
    )

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Yoqish" if not auto_cleaner_enabled else "✔️ Yoqilgan",
                callback_data='auto_cleaner_on'
            ),
            InlineKeyboardButton(
                "❌ O'chirish" if auto_cleaner_enabled else "✖️ O'chirilgan",
                callback_data='auto_cleaner_off'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        cleaner_text,
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
        [KeyboardButton("👤 Profil"), KeyboardButton("👥 O'quvchilar")],
        [KeyboardButton("📁 File Cleaner")],
        [KeyboardButton("💳 To'lovlar tarixi"), KeyboardButton("📊 Statistika")]
    ]

    keyboard.extend([
        [KeyboardButton("👥 Hamjamiyat")],
        [KeyboardButton("◀️ Ortga")]
    ])

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    message_text = update.message.text

    # Check if admin is inputting data
    from bot.handlers.payment_handlers import handle_admin_input
    admin_handled = await handle_admin_input(update, context, message_text)
    if admin_handled:
        return

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
        context.user_data['status_message'] = None # Clear status message


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

    # Check if user is creating a test
    if context.user_data.get('creating_test'):
        handled = await handle_test_input(update, context, message_text)
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
    elif message_text == "📁 File Cleaner":
        await handle_file_cleaner(update, context)
    elif message_text == "📝 Online test o'tkazish":
        await handle_public_test(update, context)
    elif message_text == "📊 Statistika":
        await handle_statistics(update, context)
    elif message_text == "💳 To'lovlar tarixi":
        from bot.handlers.payment_handlers import show_payment_history
        await show_payment_history(update, context)
    elif message_text == "👥 Hamjamiyat":
        await handle_community(update, context)
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
    elif message_text == "🧽 Auto File Cleaner":
        await handle_auto_file_cleaner(update, context)
    # Handle test creation buttons
    elif message_text == "➕ Yangi test yaratish":
        await handle_create_test(update, context)
    elif message_text == "📋 Testlarimni ko'rish":
        await handle_view_tests(update, context)
    elif message_text == "➕ Yana savol qo'shish":
        await handle_add_more_questions(update, context)
    elif message_text == "✅ Testni tugatish":
        await handle_finish_test(update, context)
    else:
        await update.message.reply_text(
            "📎 Ma'lumotlar faylini yuboring!\n\n"
            "CSV yoki Excel formatdagi faylni yuboring. "
            "Yordam kerak bo'lsa /help buyrug'ini yuboring.")
