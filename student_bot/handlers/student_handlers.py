import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.utils.test_manager import TestManager

logger = logging.getLogger(__name__)

test_manager = TestManager()

TAKING_TEST = 1
ANSWERING_QUESTION = 2


def get_main_keyboard():
    """Create main reply keyboard"""
    keyboard = [
        [KeyboardButton("📝 Mavjud testlar")],
        [KeyboardButton("📊 Mening natijalarim")],
        [KeyboardButton("📢 E'lonlar")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def format_time_remaining(minutes_remaining):
    """Format remaining time in readable format"""
    if minutes_remaining > 60:
        hours = minutes_remaining // 60
        mins = minutes_remaining % 60
        return f"{hours}h {mins}min"
    return f"{minutes_remaining} daqiqa"


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart bot - clear all states and return to main menu"""
    user_id = update.effective_user.id

    # Clear all context data
    context.user_data.clear()

    # Send restart message
    await update.message.reply_text(
        "🔄 *Bot qayta ishga tushirildi*\n\n"
        "Barcha davom etayotgan jarayonlar bekor qilindi.\n"
        "Bosh menyuga qaytdingiz.",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

    logger.info(f"Student bot restarted by user {user_id}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued"""
    user_id = update.effective_user.id
    user = update.effective_user

    # Check if user has profile with full name
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from bot.utils.student_data import StudentDataManager
    student_data_manager = StudentDataManager()
    
    # Try to get user profile
    user_profile = student_data_manager.get_student_profile(user_id)
    
    # If no full name saved, ask for it
    if not user_profile or not user_profile.get('full_name'):
        context.user_data['registering'] = True
        await update.message.reply_text(
            "👋 Xush kelibsiz!\n\n"
            "Davom etish uchun ism va familiyangizni kiriting:\n\n"
            "*Masalan:* Sardor Oktamov",
            parse_mode='Markdown'
        )
        return

    # Handle deep link if present
    if context.args and len(context.args) > 0:
        deep_link = context.args[0]
        logger.info(f"Deep link qabul qilindi: {deep_link}")
        
        if deep_link.startswith('test_'):
            test_id = deep_link
            logger.info(f"Test boshlash: {test_id}")
            await start_test(update, context, test_id)
            return

    welcome_message = (
        f"👋 Salom, *{user_profile.get('full_name', user.first_name)}*\n\n"
        "📝 *Test Platformasi*\n"
        "Online test tizimi\n\n"
        "📋 *Imkoniyatlar:*\n"
        "Testlarni topish va ishlash\n"
        "Natijalarni ko'rish\n"
        "Bilimni sinash\n\n"
        "🚀 *Boshlash:*\n"
        "Quyidagi tugmalardan foydalaning\n\n"
        "📖 /help — Yordam"
    )

    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_message = (
        "*📖 Yordam*\n\n"
        "*Asosiy funksiyalar:*\n\n"
        "📝 *Mavjud testlar* - Barcha faol testlarni ko'rish\n"
        "📊 *Mening natijalarim* - Ishlab bo'lgan testlar natijalari\n\n"
        "*Test ishlash:*\n"
        "1. 'Mavjud testlar' ni bosing\n"
        "2. Test tanlang va '▶️ Boshlash' tugmasini bosing\n"
        "3. Har bir savolga javob bering\n"
        "4. '📝 Javoblarni ko'rish' - barcha javoblarni tekshiring\n"
        "5. '✅ Testni yakunlash' - testni topshiring\n"
        "6. Natijalaringizni ko'ring\n\n"
        "*Qo'shimcha imkoniyatlar:*\n"
        "• ⏰ Qolgan vaqtni ko'rish\n"
        "• ◀️ Oldingi savol / ▶️ Keyingi savol\n"
        "• ❌ Testni bekor qilish\n\n"
        "Savollaringiz bo'lsa, o'qituvchingizga murojaat qiling!"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def handle_announcements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show announcements"""
    announcements_text = (
        "📢 *E'lonlar*\n\n"
        "🎓 *Rasch Analyzer Test Platformasi*\n\n"
        "Bu yerda yangiliklar va e'lonlar chiqadi.\n\n"
        "Hozircha yangi e'lonlar yo'q.\n\n"
        "Keyinroq qaytib kelib tekshiring!"
    )
    
    keyboard = [
        [InlineKeyboardButton("👥 Hamjamiyat", url="https://t.me/rasch_analyzer_ustozlar")],
        [InlineKeyboardButton("👨‍💼 Admin", url="https://t.me/sanjaroktamov")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        announcements_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def show_available_tests(update: Update, context: ContextTypes.DEFAULT_TYPE, subject_filter=None, page=0):
    """Show all active tests with optional subject filter and pagination"""
    # If no subject filter, show subject selection
    if not subject_filter:
        await show_subject_selection(update, context)
        return

    all_tests = test_manager._load_tests()
    active_tests = [
        (test_id, test_data)
        for test_id, test_data in all_tests.items()
        if test_data.get('is_active', False)
    ]

    # Filter by subject
    active_tests = [
        (test_id, test_data)
        for test_id, test_data in active_tests
        if subject_filter.lower() in test_data.get('subject', '').lower()
    ]

    if not active_tests:
        message_text = f"❌ '{subject_filter}' bo'yicha faol testlar topilmadi.\n\n"
        message_text += "Keyinroq qayta urinib ko'ring."

        await update.message.reply_text(message_text)
        return

    # Pagination settings
    TESTS_PER_PAGE = 5
    total_tests = len(active_tests)
    total_pages = (total_tests + TESTS_PER_PAGE - 1) // TESTS_PER_PAGE
    page = max(0, min(page, total_pages - 1))  # Ensure valid page

    start_idx = page * TESTS_PER_PAGE
    end_idx = min(start_idx + TESTS_PER_PAGE, total_tests)
    page_tests = active_tests[start_idx:end_idx]

    header = (
        f"🔍 *'{subject_filter}' bo'yicha testlar*\n\n"
        f"Jami: {total_tests} ta test\n"
        f"Sahifa: {page + 1}/{total_pages}\n\n"
        f"Testni boshlash uchun quyidagilardan birini tanlang:"
    )

    await update.message.reply_text(header, parse_mode='Markdown')

    for test_id, test_data in page_tests:
        test_text = (
            f"📋 *{test_data['name']}*\n"
            f"📚 Fan: {test_data['subject']}\n"
            f"⏱ Davomiyligi: {test_data['duration']} daqiqa\n"
            f"📝 Savollar: {len(test_data['questions'])} ta\n"
        )

        keyboard = [
            [InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_test_{test_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            test_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # Add pagination buttons if needed
    if total_pages > 1:
        pagination_buttons = []

        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton("◀️ Oldingi", callback_data=f"page_{subject_filter}_{page-1}")
            )

        if page < total_pages - 1:
            pagination_buttons.append(
                InlineKeyboardButton("Keyingi ▶️", callback_data=f"page_{subject_filter}_{page+1}")
            )

        if pagination_buttons:
            keyboard = [pagination_buttons]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Sahifa {page + 1}/{total_pages}",
                reply_markup=reply_markup
            )


async def show_subject_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show subject selection for test filtering"""
    from bot.utils.subject_sections import get_all_subjects

    subjects = get_all_subjects()

    # Get unique subjects from active tests
    all_tests = test_manager._load_tests()
    active_subjects = set()
    for test_data in all_tests.values():
        if test_data.get('is_active', False):
            active_subjects.add(test_data.get('subject', ''))

    # Filter to only show subjects with active tests
    available_subjects = [s for s in subjects if s in active_subjects]

    if not available_subjects:
        await update.message.reply_text(
            "❌ Hozirda faol testlar yo'q.\n\n"
            "Keyinroq qayta urinib ko'ring."
        )
        return

    text = (
        "📚 *Fanlarni tanlang*\n\n"
        "Qaysi fanga oid testlarni ko'rmoqchisiz?"
    )

    # Create keyboard with subject buttons (2 per row)
    keyboard = []
    for i in range(0, len(available_subjects), 2):
        row = []
        row.append(InlineKeyboardButton(
            available_subjects[i], 
            callback_data=f"subject_filter_{available_subjects[i]}"
        ))
        if i + 1 < len(available_subjects):
            row.append(InlineKeyboardButton(
                available_subjects[i + 1], 
                callback_data=f"subject_filter_{available_subjects[i + 1]}"
            ))
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def search_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search tests by subject"""
    await update.message.reply_text(
        "🔍 *Test qidirish*\n\n"
        "Fan nomini kiriting:\n\n"
        "Masalan: Matematika, Fizika, Ona tili",
        parse_mode='Markdown'
    )
    context.user_data['searching_tests'] = True


async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE, test_id: str):
    """Start taking a test"""
    logger.info(f"Start_test chaqirildi. Test ID: {test_id}")
    
    test = test_manager.get_test(test_id)
    user_id = update.effective_user.id

    # Get message object correctly (works for both message and callback_query)
    message = update.callback_query.message if update.callback_query else update.message

    if not test:
        logger.error(f"Test topilmadi! Test ID: {test_id}")
        
        # Debug: barcha testlarni ko'rish
        all_tests = test_manager._load_tests()
        logger.info(f"Mavjud testlar soni: {len(all_tests)}")
        if all_tests:
            logger.info(f"Mavjud test ID'lar: {list(all_tests.keys())[:5]}")
        
        await message.reply_text(
            f"❌ Test topilmadi!\n\n"
            f"Test ID: `{test_id}`\n\n"
            f"Iltimos, test havolasini qayta tekshiring yoki o'qituvchingizga murojaat qiling.",
            parse_mode='Markdown'
        )
        return

    if not test.get('is_active', False):
        await message.reply_text("❌ Bu test hozirda faol emas!")
        return

    time_check = test_manager.is_test_time_valid(test_id)
    if not time_check['valid']:
        await message.reply_text(f"❌ {time_check['message']}")
        return

    if test_manager.has_student_taken_test(test_id, user_id):
        if not test.get('allow_retake', False):
            await message.reply_text(
                "❌ Siz allaqachon ushbu testni topshirgansiz.\n\n"
                "Qayta topshirish mumkin emas."
            )
            return
        else:
            await message.reply_text(
                "⚠️ Siz bu testni qayta topshiryapsiz.\n"
                "Oldingi natijangiz o'chiriladi."
            )

    context.user_data['current_test_id'] = test_id
    context.user_data['current_question_index'] = 0
    context.user_data['answers'] = [-1] * len(test['questions'])
    context.user_data['taking_test'] = True
    context.user_data['test_started_at'] = datetime.now().isoformat()

    intro_text = (
        f"📝 *{test['name']}* testini boshlaysiz\n\n"
        f"📚 Fan: {test['subject']}\n"
        f"⏱ Davomiyligi: {test['duration']} daqiqa\n"
        f"📝 Savollar soni: {len(test['questions'])} ta\n\n"
    )

    if time_check.get('message') != 'OK':
        intro_text += f"⏰ {time_check['message']}\n\n"

    intro_text += (
        "*Yangi imkoniyatlar:*\n"
        "• Savollar o'rtasida harakatlanish\n"
        "• Barcha javoblarni ko'rib chiqish\n"
        "• Qolgan vaqtni kuzatish\n\n"
        "Tayyor bo'lsangiz, 'Boshlash' tugmasini bosing!"
    )

    keyboard = [
        [InlineKeyboardButton("▶️ Boshlash", callback_data=f"begin_test_{test_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(intro_text, parse_mode='Markdown', reply_markup=reply_markup)


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current question with navigation"""
    test_id = context.user_data.get('current_test_id')
    question_index = context.user_data.get('current_question_index', 0)

    test = test_manager.get_test(test_id)

    if test_id:
        time_check = test_manager.is_test_time_valid(test_id)
        if not time_check['valid']:
            message = update.callback_query.message if update.callback_query else update.message
            await message.reply_text(
                f"⏰ {time_check['message']}\n\n"
                "Testingiz avtomatik yakunlanmoqda..."
            )
            await finish_test(update, context, auto_submit=True)
            return

    if not test:
        return

    if question_index >= len(test['questions']):
        question_index = len(test['questions']) - 1
        context.user_data['current_question_index'] = question_index

    question = test['questions'][question_index]
    answers = context.user_data.get('answers', [-1] * len(test['questions']))

    answered_count = sum(1 for a in answers if a != -1)
    progress_bar = f"[{'█' * answered_count}{'░' * (len(test['questions']) - answered_count)}]"

    test_started = datetime.fromisoformat(context.user_data.get('test_started_at'))
    elapsed = datetime.now() - test_started
    remaining_minutes = test['duration'] - int(elapsed.total_seconds() / 60)

    time_icon = "⏰"
    if remaining_minutes < 5:
        time_icon = "🔴"
    elif remaining_minutes < 10:
        time_icon = "🟡"

    # Check if this is a text answer question (only 1 option)
    is_text_answer = len(question['options']) == 1

    question_text = (
        f"❓ *Savol {question_index + 1}/{len(test['questions'])}*\n"
        f"{time_icon} Qolgan vaqt: {remaining_minutes} daqiqa\n"
        f"{progress_bar} {answered_count}/{len(test['questions'])}\n\n"
        f"{question['text']}\n\n"
    )

    if is_text_answer:
        # Text answer question - show instruction to type
        current_answer = answers[question_index]
        if current_answer != -1:
            # Show current answer
            stored_answer = context.user_data.get('text_answers', {}).get(str(question_index), '')
            question_text += f"✅ *Sizning javobingiz:* {stored_answer}\n\n"

        question_text += "✍️ *Javobingizni chatga yozing:*\n"
        question_text += "Matn yoki raqam yozishingiz mumkin.\n\n"

    keyboard = []

    if not is_text_answer:
        # Multiple choice question - show option buttons
        current_answer = answers[question_index]

        for i, option in enumerate(question['options']):
            mark = "✅ " if current_answer == i else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{mark}{chr(65 + i)}) {option}",
                    callback_data=f"answer_{question_index}_{i}"
                )
            ])

    # Navigation buttons
    nav_buttons = []
    if question_index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"nav_prev"))
    if question_index < len(test['questions']) - 1:
        nav_buttons.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"nav_next"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Review and cancel buttons
    keyboard.append([
        InlineKeyboardButton("📝 Javoblarni ko'rish", callback_data="review_answers"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_test")
    ])

    # Check if all questions answered - suggest completion
    if answered_count == len(test['questions']):
        keyboard.insert(-1, [
            InlineKeyboardButton("✅ Barcha savollar javoblandi - Tugatish", callback_data="confirm_submit")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = update.callback_query.message if update.callback_query else update.message

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                question_text, 
                parse_mode='Markdown', 
                reply_markup=reply_markup
            )
        else:
            await message.reply_text(
                question_text, 
                parse_mode='Markdown', 
                reply_markup=reply_markup
            )
    except Exception:
        await message.reply_text(
            question_text, 
            parse_mode='Markdown', 
            reply_markup=reply_markup
        )


async def review_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all answers for review"""
    query = update.callback_query
    await query.answer()

    test_id = context.user_data.get('current_test_id')
    answers = context.user_data.get('answers', [])
    text_answers = context.user_data.get('text_answers', {})

    test = test_manager.get_test(test_id)
    if not test:
        return

    answered_count = sum(1 for a in answers if a != -1)
    unanswered = len(answers) - answered_count
    unanswered_indices = [i for i, a in enumerate(answers) if a == -1]

    review_text = (
        f"📝 *Javoblaringiz*\n\n"
        f"✅ Javob berilgan: {answered_count}\n"
        f"❓ Javob berilmagan: {unanswered}\n\n"
    )

    for i, answer_idx in enumerate(answers):
        if answer_idx != -1:
            question = test['questions'][i]
            # Check if it's a text answer
            if len(question['options']) == 1:
                # Text answer
                text_answer = text_answers.get(str(i), question['options'][0])
                review_text += f"{i+1}. ✍️ {text_answer[:30]}...\n"
            else:
                # Multiple choice
                answer_text = question['options'][answer_idx]
                review_text += f"{i+1}. {chr(65 + answer_idx)}) {answer_text[:30]}...\n"
        else:
            review_text += f"{i+1}. ❌ Javob berilmagan\n"

    keyboard = []

    # If there are unanswered questions, add button to go to first unanswered
    if unanswered_indices:
        first_unanswered = unanswered_indices[0]
        keyboard.append([
            InlineKeyboardButton(
                f"❓ {first_unanswered + 1}-savolga o'tish", 
                callback_data=f"goto_{first_unanswered}"
            )
        ])

    keyboard.append([InlineKeyboardButton("✅ Testni yakunlash", callback_data="confirm_submit")])
    keyboard.append([InlineKeyboardButton("◀️ Testga qaytish", callback_data="back_to_test")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        review_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int, answer_index: int):
    """Handle student answer"""
    query = update.callback_query
    await query.answer("✅ Javob saqlandi!")

    test_id = context.user_data.get('current_test_id')
    if test_id:
        time_check = test_manager.is_test_time_valid(test_id)
        if not time_check['valid']:
            await query.message.reply_text(
                f"⏰ {time_check['message']}\n\n"
                "Testingiz avtomatik yakunlanmoqda..."
            )
            await finish_test(update, context, auto_submit=True)
            return

    answers = context.user_data.get('answers', [])
    answers[question_index] = answer_index
    context.user_data['answers'] = answers

    await show_question(update, context)


async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE, auto_submit: bool = False):
    """Finish test and show detailed results"""
    test_id = context.user_data.get('current_test_id')
    answers = context.user_data.get('answers', [])
    user_id = update.effective_user.id

    if auto_submit:
        test = test_manager.get_test(test_id)
        if test:
            total_questions = len(test['questions'])
            while len(answers) < total_questions:
                answers.append(-1)

    results = test_manager.submit_answer(test_id, user_id, answers)

    if 'error' in results:
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text(f"❌ Xatolik: {results['error']}")
        return

    context.user_data['taking_test'] = False
    context.user_data['current_test_id'] = None
    context.user_data['current_question_index'] = 0
    context.user_data['answers'] = []
    context.user_data['test_started_at'] = None

    test = test_manager.get_test(test_id)
    text_answers = context.user_data.get('text_answers', {})
    context.user_data['text_answers'] = {}  # Clear text answers
    correct_answers = []
    incorrect_answers = []

    for i, answer_idx in enumerate(answers):
        question = test['questions'][i]
        correct_idx = question['correct_answer']

        # Check if it's a text answer question
        if len(question['options']) == 1 and answer_idx != -1:
            # Text answer - compare the text
            correct_text = question['options'][0].strip().lower()
            user_text = text_answers.get(str(i), '').strip().lower()

            if user_text == correct_text:
                correct_answers.append(i + 1)
            else:
                incorrect_answers.append(i + 1)
        elif answer_idx == correct_idx:
            # Multiple choice - compare index
            correct_answers.append(i + 1)
        elif answer_idx != -1:
            incorrect_answers.append(i + 1)

    results_text = ""

    if auto_submit:
        results_text += "⏰ *Test vaqti tugadi! Avtomatik topshirildi.*\n\n"
    else:
        results_text += "✅ *Test yakunlandi!*\n\n"

    results_text += (
        f"📊 *Natijangiz:*\n"
        f"• Ball: {results['score']}/{results['max_score']}\n"
        f"• Foiz: {results['percentage']:.1f}%\n"
        f"• To'g'ri: {len(correct_answers)} ta\n"
        f"• Noto'g'ri: {len(incorrect_answers)} ta\n"
        f"• Javob berilmagan: {len(answers) - len(correct_answers) - len(incorrect_answers)} ta\n\n"
    )

    if results['percentage'] >= 90:
        results_text += "🌟 Ajoyib natija! Tabriklaymiz!"
    elif results['percentage'] >= 70:
        results_text += "👍 Yaxshi natija!"
    elif results['percentage'] >= 50:
        results_text += "📚 Yaxshi, lekin ko'proq mashq qilishingiz kerak."
    else:
        results_text += "💪 Mashq qilishda davom eting!"

    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(
        results_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def show_my_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show student's test results history"""
    user_id = update.effective_user.id

    all_tests = test_manager._load_tests()

    my_results = []
    for test_id, test_data in all_tests.items():
        participants = test_data.get('participants', {})

        # Handle both dict and list formats for backward compatibility
        if isinstance(participants, dict):
            user_id_str = str(user_id)
            if user_id_str in participants:
                participant = participants[user_id_str]
                if isinstance(participant, dict) and participant.get('submitted'):
                    my_results.append({
                        'test_name': test_data['name'],
                        'subject': test_data['subject'],
                        'score': participant.get('score', 0),
                        'max_score': participant.get('max_score', 0),
                        'percentage': participant.get('percentage', 0),
                        'submitted_at': participant.get('submitted_at', '')[:10]
                    })
        elif isinstance(participants, list):
            for participant in participants:
                if participant.get('student_id') == user_id:
                    my_results.append({
                        'test_name': test_data['name'],
                        'subject': test_data['subject'],
                        'score': participant.get('score', 0),
                        'max_score': participant.get('max_score', 0),
                        'percentage': participant.get('percentage', 0),
                        'submitted_at': participant.get('submitted_at', '')[:10]
                    })

    if not my_results:
        await update.message.reply_text(
            "📊 Sizda hali test natijalari yo'q.\n\n"
            "Testlarni ishlashni boshlang!"
        )
        return

    my_results.sort(key=lambda x: x['submitted_at'], reverse=True)

    results_text = f"📊 *Mening natijalarim* ({len(my_results)} ta test)\n\n"

    for idx, result in enumerate(my_results[:10], 1):
        emoji = "🥇" if result['percentage'] >= 90 else "🥈" if result['percentage'] >= 70 else "🥉" if result['percentage'] >= 50 else "📝"
        results_text += (
            f"{emoji} *{result['test_name']}*\n"
            f"📚 {result['subject']}\n"
            f"• Ball: {result['score']}/{result['max_score']} ({result['percentage']:.1f}%)\n"
            f"📅 {result['submitted_at']}\n\n"
        )

    if len(my_results) > 10:
        results_text += f"_... va yana {len(my_results) - 10} ta natija_"

    await update.message.reply_text(results_text, parse_mode='Markdown')


async def cancel_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel ongoing test"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("✅ Ha, bekor qilish", callback_data="confirm_cancel"),
            InlineKeyboardButton("❌ Yo'q, davom etish", callback_data="back_to_test")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⚠️ *Testni bekor qilmoqchimisiz?*\n\n"
        "Barcha javoblaringiz o'chiriladi va test topshirilmaydi.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm test cancellation"""
    query = update.callback_query
    await query.answer()

    context.user_data['taking_test'] = False
    context.user_data['current_test_id'] = None
    context.user_data['current_question_index'] = 0
    context.user_data['answers'] = []
    context.user_data['test_started_at'] = None
    context.user_data['text_answers'] = {}

    await query.edit_message_text(
        "❌ Test bekor qilindi.\n\n"
        "Bosh menyuga qaytdingiz.",
        reply_markup=get_main_keyboard()
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline buttons"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('start_test_'):
        test_id = query.data.replace('start_test_', '')
        await start_test(update, context, test_id)

    elif query.data.startswith('begin_test_'):
        test_id = query.data.replace('begin_test_', '')
        test = test_manager.get_test(test_id)
        context.user_data['current_test_id'] = test_id
        context.user_data['current_question_index'] = 0
        context.user_data['answers'] = [-1] * len(test['questions'])
        context.user_data['taking_test'] = True
        context.user_data['test_started_at'] = datetime.now().isoformat()

        # Send PDF file if available
        pdf_file_path = test.get('pdf_file_path')
        if pdf_file_path and os.path.exists(pdf_file_path):
            try:
                with open(pdf_file_path, 'rb') as pdf_file:
                    await query.message.reply_document(
                        document=pdf_file,
                        caption="📄 Test savollari fayli"
                    )
            except Exception as e:
                logger.error(f"Error sending PDF file: {str(e)}")

        await show_question(update, context)

    elif query.data.startswith('answer_'):
        parts = query.data.split('_')
        question_index = int(parts[1])
        answer_index = int(parts[2])
        await handle_answer(update, context, question_index, answer_index)

    elif query.data == 'nav_prev':
        context.user_data['current_question_index'] -= 1
        await show_question(update, context)

    elif query.data == 'nav_next':
        context.user_data['current_question_index'] += 1
        await show_question(update, context)

    elif query.data == 'review_answers':
        await review_answers(update, context)

    elif query.data == 'back_to_test':
        await show_question(update, context)

    elif query.data == 'cancel_test':
        await cancel_test(update, context)

    elif query.data == 'confirm_cancel':
        await confirm_cancel(update, context)

    elif query.data == 'confirm_submit':
        answers = context.user_data.get('answers', [])
        unanswered = sum(1 for a in answers if a == -1)

        if unanswered > 0:
            keyboard = [
                [InlineKeyboardButton("✅ Ha, topshirish", callback_data="force_submit")],
                [InlineKeyboardButton("◀️ Testga qaytish", callback_data="back_to_test")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"⚠️ *Diqqat!*\n\n"
                f"Siz {unanswered} ta savolga javob bermadingiz.\n\n"
                f"Baribir testni topshirasizmi?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await finish_test(update, context)

    elif query.data == 'force_submit':
        await finish_test(update, context)

    elif query.data.startswith('goto_'):
        question_index = int(query.data.replace('goto_', ''))
        context.user_data['current_question_index'] = question_index
        await show_question(update, context)

    elif query.data.startswith('subject_filter_'):
        subject = query.data.replace('subject_filter_', '')
        await query.answer(f"📚 {subject}")
        # Create a fake update with message for show_available_tests
        fake_update = Update(
            update_id=update.update_id,
            message=query.message
        )
        await show_available_tests(fake_update, context, subject_filter=subject, page=0)

    elif query.data.startswith('page_'):
        parts = query.data.split('_')
        if len(parts) >= 3:
            subject = '_'.join(parts[1:-1])  # Handle subjects with underscores
            page = int(parts[-1])
            await query.answer(f"Sahifa {page + 1}")
            # Create a fake update with message for show_available_tests
            fake_update = Update(
                update_id=update.update_id,
                message=query.message
            )
            await show_available_tests(fake_update, context, subject_filter=subject, page=page)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    message_text = update.message.text
    user_id = update.effective_user.id

    # Handle registration (name collection)
    if context.user_data.get('registering'):
        # Validate name (at least 2 words, each with at least 2 letters)
        name_parts = message_text.strip().split()
        
        # Check if at least 2 words
        if len(name_parts) < 2:
            await update.message.reply_text(
                "❌ Iltimos, ism va familiyangizni to'liq kiriting.\n\n"
                "🔹 *To'g'ri misol:* Sardor Oktamov\n"
                "🔹 *To'g'ri misol:* Aziza Rahimova",
                parse_mode='Markdown'
            )
            return
        
        # Check if each part has at least 2 characters and contains only letters
        valid = True
        for part in name_parts[:2]:  # Check first 2 words
            # Remove common Uzbek/Russian letter variations for validation
            cleaned_part = ''.join(c for c in part if c.isalpha() or c in "''`-")
            if len(cleaned_part) < 2:
                valid = False
                break
        
        if not valid:
            await update.message.reply_text(
                "❌ Ism va familiya har biri kamida 2 ta harfdan iborat bo'lishi kerak.\n\n"
                "🔹 *To'g'ri misol:* Sardor Oktamov\n"
                "🔹 *To'g'ri misol:* Aziza Rahimova\n"
                "🔹 *To'g'ri misol:* Muhammad Ali",
                parse_mode='Markdown'
            )
            return

        # Save user profile
        from bot.utils.student_data import StudentDataManager
        student_data_manager = StudentDataManager()
        
        student_data_manager.save_student_profile(user_id, {
            'full_name': message_text.strip(),
            'telegram_id': user_id,
            'username': update.effective_user.username,
            'registered_at': datetime.now().isoformat()
        })

        context.user_data['registering'] = False

        await update.message.reply_text(
            f"✅ Ro'yxatdan o'tdingiz!\n\n"
            f"👤 {message_text.strip()}\n\n"
            "Endi testlarni ishlashingiz mumkin.",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return

    # Check if user is taking a test and current question is text answer
    if context.user_data.get('taking_test'):
        test_id = context.user_data.get('current_test_id')
        question_index = context.user_data.get('current_question_index', 0)

        test = test_manager.get_test(test_id)
        if test:
            question = test['questions'][question_index]

            # Check if this is a text answer question (only 1 option)
            if len(question['options']) == 1:
                # Save the text answer
                answers = context.user_data.get('answers', [-1] * len(test['questions']))
                answers[question_index] = 0  # Mark as answered (index 0 since only 1 option)
                context.user_data['answers'] = answers

                # Store the actual text answer
                text_answers = context.user_data.get('text_answers', {})
                text_answers[str(question_index)] = message_text
                context.user_data['text_answers'] = text_answers

                # Show confirmation and current question
                await update.message.reply_text(
                    f"✅ Javob qabul qilindi: {message_text}\n\n"
                    f"Keyingi savolga o'tish uchun tugmani bosing."
                )
                await show_question(update, context)
                return

    if context.user_data.get('searching_tests'):
        context.user_data['searching_tests'] = False
        await show_available_tests(update, context, subject_filter=message_text, page=0)
        return

    if message_text == "📝 Mavjud testlar":
        await show_available_tests(update, context)
    elif message_text == "📊 Mening natijalarim":
        await show_my_results(update, context)
    elif message_text == "📢 E'lonlar":
        await handle_announcements(update, context)
    else:
        await update.message.reply_text(
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_keyboard()
        )