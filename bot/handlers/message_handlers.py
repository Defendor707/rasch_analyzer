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
    user_name = update.effective_user.first_name or "foydalanuvchi"
    
    welcome_message = (
        f"👋 Assalomu alaykum, {user_name}!\n\n"
        "🎓 Rasch analiyzer botga xush kelibsiz!\n\n"
        "📝 Matritsani yuboring yoki /namuna buyrug'i bilan namuna tahlilni ko'ring\n\n"
        "/help commandasini yuborib foydalanish yo'riqnomasi bilan tanishing."
    )
    
    file_info_message = (
        "📊 Excel (.xls, .xlsx, .csv) faylni yuborishingiz mumkin!"
    )
    
    await update.message.reply_text(welcome_message)
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
        
        # Generate person results report
        person_pdf_path = pdf_generator.generate_person_results_report(
            results,
            filename=f"namuna_talabgorlar_{user_id}"
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
