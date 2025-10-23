import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
import os

# Add parent directory to path to import from bot.utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.utils.test_manager import TestManager

logger = logging.getLogger(__name__)

# Initialize test manager
test_manager = TestManager()

# Test states
TAKING_TEST = 1
ANSWERING_QUESTION = 2


def get_main_keyboard():
    """Create main reply keyboard"""
    keyboard = [
        [KeyboardButton("📝 Mavjud testlar")],
        [KeyboardButton("📊 Mening natijalarim")],
        [KeyboardButton("ℹ️ Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued"""
    user = update.effective_user

    # Check if starting a test via deep link
    if context.args and context.args[0].startswith('test_'):
        test_id = context.args[0]
        await start_test(update, context, test_id)
        return

    welcome_message = (
        f"👋 Assalomu alaykum, {user.first_name}!\n\n"
        "📝 Test botiga xush kelibsiz!\n\n"
        "Bu bot orqali siz:\n"
        "• Ommaviy testlarni topishingiz\n"
        "• Testlarni ishlashingiz\n"
        "• Natijalaringizni ko'rishingiz mumkin\n\n"
        "Boshlash uchun quyidagi tugmalardan foydalaning!"
    )

    await update.message.reply_text(
        welcome_message,
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
        "1. 'Mavjud testlar' tugmasini bosing\n"
        "2. Test tanlang va 'Boshlash' tugmasini bosing\n"
        "3. Har bir savolga javob bering\n"
        "4. Test tugagach natijangizni ko'ring\n\n"
        "Savollaringiz bo'lsa, o'qituvchingizga murojaat qiling!"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def show_available_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all active tests"""
    # Get all active tests from test_manager
    all_tests = test_manager._load_tests()
    active_tests = [
        (test_id, test_data)
        for test_id, test_data in all_tests.items()
        if test_data.get('is_active', False)
    ]

    if not active_tests:
        await update.message.reply_text(
            "❌ Hozirda faol testlar yo'q.\n\n"
            "Keyinroq qayta urinib ko'ring."
        )
        return

    await update.message.reply_text(
        f"📝 *Mavjud testlar* ({len(active_tests)} ta)\n\n"
        "Testni boshlash uchun quyidagilardan birini tanlang:",
        parse_mode='Markdown'
    )

    for test_id, test_data in active_tests:
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


async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE, test_id: str):
    """Start taking a test"""
    test = test_manager.get_test(test_id)

    if not test:
        await update.message.reply_text("❌ Test topilmadi!")
        return

    if not test.get('is_active', False):
        await update.message.reply_text("❌ Bu test hozirda faol emas!")
        return

    # Initialize test session
    context.user_data['current_test_id'] = test_id
    context.user_data['current_question_index'] = 0
    context.user_data['answers'] = []
    context.user_data['taking_test'] = True

    intro_text = (
        f"📝 *{test['name']}* testini boshlaysiz\n\n"
        f"📚 Fan: {test['subject']}\n"
        f"⏱ Davomiyligi: {test['duration']} daqiqa\n"
        f"📝 Savollar soni: {len(test['questions'])} ta\n\n"
        "Tayyor bo'lsangiz, 'Boshlash' tugmasini bosing!"
    )

    keyboard = [
        [InlineKeyboardButton("▶️ Boshlash", callback_data=f"begin_test_{test_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(intro_text, parse_mode='Markdown', reply_markup=reply_markup)


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current question"""
    test_id = context.user_data.get('current_test_id')
    question_index = context.user_data.get('current_question_index', 0)

    test = test_manager.get_test(test_id)
    if not test or question_index >= len(test['questions']):
        await finish_test(update, context)
        return

    question = test['questions'][question_index]

    question_text = (
        f"❓ *Savol {question_index + 1}/{len(test['questions'])}*\n\n"
        f"{question['text']}\n\n"
    )

    # Create option buttons
    keyboard = []
    for i, option in enumerate(question['options']):
        keyboard.append([
            InlineKeyboardButton(
                f"{chr(65 + i)}) {option}",
                callback_data=f"answer_{question_index}_{i}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(question_text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int, answer_index: int):
    """Handle student answer"""
    query = update.callback_query
    await query.answer()

    # Save answer
    answers = context.user_data.get('answers', [])
    answers.append(answer_index)
    context.user_data['answers'] = answers

    # Move to next question
    context.user_data['current_question_index'] = question_index + 1

    await show_question(update, context)


async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish test and show results"""
    test_id = context.user_data.get('current_test_id')
    answers = context.user_data.get('answers', [])
    user_id = update.effective_user.id

    # Submit answers and get results
    results = test_manager.submit_answer(test_id, user_id, answers)

    if 'error' in results:
        await update.callback_query.message.reply_text(
            f"❌ Xatolik: {results['error']}"
        )
        return

    # Clear test session
    context.user_data['taking_test'] = False
    context.user_data['current_test_id'] = None
    context.user_data['current_question_index'] = 0
    context.user_data['answers'] = []

    # Show results
    results_text = (
        f"✅ *Test yakunlandi!*\n\n"
        f"📊 *Natijangiz:*\n"
        f"• Ball: {results['score']}/{results['max_score']}\n"
        f"• Foiz: {results['percentage']:.1f}%\n\n"
    )

    # Add performance message
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

    # Get all tests
    all_tests = test_manager._load_tests()

    # Find tests this student has taken
    my_results = []
    for test_id, test_data in all_tests.items():
        for participant in test_data.get('participants', []):
            if participant['student_id'] == user_id:
                my_results.append({
                    'test_name': test_data['name'],
                    'subject': test_data['subject'],
                    'score': participant['score'],
                    'max_score': participant['max_score'],
                    'percentage': participant['percentage'],
                    'submitted_at': participant['submitted_at'][:10]
                })

    if not my_results:
        await update.message.reply_text(
            "📊 Sizda hali test natijalari yo'q.\n\n"
            "Testlarni ishlashni boshlang!"
        )
        return

    results_text = f"📊 *Mening natijalarim* ({len(my_results)} ta test)\n\n"

    for result in my_results:
        results_text += (
            f"📋 *{result['test_name']}*\n"
            f"📚 Fan: {result['subject']}\n"
            f"• Ball: {result['score']}/{result['max_score']}\n"
            f"• Foiz: {result['percentage']:.1f}%\n"
            f"📅 Sana: {result['submitted_at']}\n\n"
        )

    await update.message.reply_text(results_text, parse_mode='Markdown')


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline buttons"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('start_test_'):
        test_id = query.data.replace('start_test_', '')
        await start_test(update, context, test_id)

    elif query.data.startswith('begin_test_'):
        test_id = query.data.replace('begin_test_', '')
        context.user_data['current_test_id'] = test_id
        context.user_data['current_question_index'] = 0
        context.user_data['answers'] = []
        context.user_data['taking_test'] = True
        await show_question(update, context)

    elif query.data.startswith('answer_'):
        parts = query.data.split('_')
        question_index = int(parts[1])
        answer_index = int(parts[2])
        await handle_answer(update, context, question_index, answer_index)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    message_text = update.message.text

    if message_text == "📝 Mavjud testlar":
        await show_available_tests(update, context)
    elif message_text == "📊 Mening natijalarim":
        await show_my_results(update, context)
    elif message_text == "ℹ️ Yordam":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_keyboard()
        )