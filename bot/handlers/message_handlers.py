import os
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.rasch_analysis import RaschAnalyzer
from bot.utils.pdf_generator import PDFReportGenerator
import logging

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued"""
    welcome_message = (
        "👋 *Rasch Model Tahlil Boti*\n\n"
        "Men sizning ma'lumotlaringizni Rasch modeli yordamida tahlil qilaman "
        "va PDF formatda natijalarni taqdim etaman.\n\n"
        "*Qanday foydalanish kerak:*\n"
        "1️⃣ Ma'lumotlar faylini yuboring (CSV yoki Excel)\n"
        "2️⃣ Tahlil tugashini kuting\n"
        "3️⃣ PDF hisobot  olasiz\n\n"
        "*Fayl formati:*\n"
        "- Qatorlar: Ishtirokchilar\n"
        "- Ustunlar: Savollar/Itemlar\n"
        "- Qiymatlar: 0 (noto'g'ri) yoki 1 (to'g'ri)\n\n"
        "*Buyruqlar:*\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam\n\n"
        "Faylni yuboring va boshlaylik! 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


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
        
        numeric_data = data.select_dtypes(include=['number'])
        if numeric_data.empty:
            numeric_data = data.iloc[:, :].apply(pd.to_numeric, errors='coerce')
        
        numeric_data = numeric_data.fillna(0)
        
        if not all(numeric_data.isin([0, 1]).all()):
            await update.message.reply_text(
                "⚠️ Ogohlantirish: Ma'lumotlar 0 va 1 dan boshqa qiymatlarni o'z ichiga oladi.\n"
                "Rasch modeli uchun faqat dikotomik ma'lumotlar (0/1) talab qilinadi.\n"
                "Davom etmoqdamiz, lekin natijalar noto'g'ri bo'lishi mumkin."
            )
        
        analyzer = RaschAnalyzer()
        results = analyzer.fit(numeric_data)
        
        summary_text = analyzer.get_summary(results)
        
        pdf_generator = PDFReportGenerator()
        
        # Generate general statistics report
        general_pdf_path = pdf_generator.generate_report(
            results,
            filename=f"umumiy_statistika_{user_id}"
        )
        
        # Generate person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename=f"talabgorlar_natijalari_{user_id}"
        )
        
        await update.message.reply_text(
            f"✅ *Tahlil tugallandi!*\n\n"
            f"📊 Ishtirokchilar soni: {results['n_persons']}\n"
            f"📝 Itemlar soni: {results['n_items']}\n"
            f"📈 Reliability: {results['reliability']:.3f}\n\n"
            f"Ikkita PDF hisobot yuborilmoqda...",
            parse_mode='Markdown'
        )
        
        # Send general statistics PDF
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
                caption="👥 Talabgorlar natijalari (T-Score bo'yicha tartiblangan)"
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    await update.message.reply_text(
        "📎 Ma'lumotlar faylini yuboring!\n\n"
        "CSV yoki Excel formatdagi faylni yuboring. "
        "Yordam kerak bo'lsa /help buyrug'ini yuboring."
    )
