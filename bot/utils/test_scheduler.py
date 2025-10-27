import logging
import pandas as pd
from telegram.ext import Application
from typing import Optional
from .test_manager import TestManager
from .rasch_analysis import RaschAnalyzer
from .pdf_generator import PDFReportGenerator
from .user_data import UserDataManager

logger = logging.getLogger(__name__)


async def check_and_finalize_expired_tests(application: Application) -> None:
    """
    Check for expired tests and send analysis results to teachers
    
    Args:
        application: Telegram bot application instance
    """
    test_manager = TestManager()
    expired_test_ids = test_manager.get_expired_tests()
    
    if not expired_test_ids:
        logger.info("Tugagan testlar topilmadi")
        return
    
    logger.info(f"Tugagan testlar topildi: {len(expired_test_ids)}")
    
    for test_id in expired_test_ids:
        try:
            await process_and_send_test_results(application, test_id)
        except Exception as e:
            logger.error(f"Test {test_id} natijalarini yuborishda xatolik: {e}")
            continue


async def process_and_send_test_results(application: Application, test_id: str) -> None:
    """
    Process test results, perform Rasch analysis, and send to teacher
    
    Args:
        application: Telegram bot application instance
        test_id: Test identifier
    """
    test_manager = TestManager()
    user_data_manager = UserDataManager()
    
    # Get test info
    test = test_manager.get_test(test_id)
    if not test:
        logger.error(f"Test {test_id} topilmadi")
        return
    
    teacher_id = test.get('teacher_id')
    if not teacher_id:
        logger.error(f"Test {test_id} uchun o'qituvchi ID topilmadi")
        return
    
    # Finalize the test first
    test_manager.finalize_test(test_id)
    logger.info(f"Test {test_id} yakunlandi")
    
    # Get test results matrix
    results_data = test_manager.get_test_results_matrix(test_id)
    
    if not results_data or not results_data.get('matrix'):
        # No participants or no submissions
        await application.bot.send_message(
            chat_id=teacher_id,
            text=f"📊 *Test yakunlandi*\n\n"
                 f"📋 Test nomi: {test['name']}\n"
                 f"📚 Fan: {test['subject']}\n\n"
                 f"⚠️ Testni hech kim topshirmadi yoki kamida 2 ta ishtirokchi kerak.\n\n"
                 f"Rasch tahlili uchun kamida 2 ta ishtirokchi va 2 ta savol kerak.",
            parse_mode='Markdown'
        )
        return
    
    # Check minimum requirements for Rasch analysis
    n_participants = results_data['n_participants']
    n_questions = results_data['n_questions']
    
    if n_participants < 2 or n_questions < 2:
        await application.bot.send_message(
            chat_id=teacher_id,
            text=f"📊 *Test yakunlandi*\n\n"
                 f"📋 Test nomi: {test['name']}\n"
                 f"📚 Fan: {test['subject']}\n"
                 f"👥 Ishtirokchilar: {n_participants} ta\n"
                 f"📝 Savollar: {n_questions} ta\n\n"
                 f"⚠️ Rasch tahlili uchun kamida 2 ta ishtirokchi va 2 ta savol kerak.",
            parse_mode='Markdown'
        )
        return
    
    # Perform Rasch analysis
    try:
        await application.bot.send_message(
            chat_id=teacher_id,
            text=f"📊 *Test avtomatik yakunlandi*\n\n"
                 f"📋 {test['name']}\n"
                 f"📚 Fan: {test['subject']}\n"
                 f"👥 Ishtirokchilar: {n_participants} ta\n\n"
                 f"⏳ Rasch tahlili bajarilmoqda...",
            parse_mode='Markdown'
        )
        
        # Prepare data for analysis
        df = pd.DataFrame(
            results_data['matrix'],
            columns=results_data['item_names']
        )
        
        # Perform Rasch analysis
        analyzer = RaschAnalyzer()
        analysis_results = analyzer.fit(df)
        
        # Generate PDF reports
        pdf_generator = PDFReportGenerator()
        
        # Get user data for section results
        user_data = user_data_manager.get_user_data(teacher_id)
        section_results_enabled = user_data.get('section_results_enabled', False)
        section_questions = user_data.get('section_questions', {})
        
        # Generate item parameters report
        item_pdf_path = pdf_generator.generate_item_parameters_report(
            analysis_results,
            filename=f"test_{test_id}_items"
        )
        
        with open(item_pdf_path, 'rb') as pdf_file:
            await application.bot.send_document(
                chat_id=teacher_id,
                document=pdf_file,
                filename=f"{test['name']}_item_parameters.pdf",
                caption="📊 Savol parametrlari va umumiy statistika"
            )
        
        # Generate person statistics report
        person_pdf_path = pdf_generator.generate_person_statistics_report(
            analysis_results,
            filename=f"test_{test_id}_persons"
        )
        
        with open(person_pdf_path, 'rb') as pdf_file:
            await application.bot.send_document(
                chat_id=teacher_id,
                document=pdf_file,
                filename=f"{test['name']}_person_statistics.pdf",
                caption="👥 Talabgorlar natijalari"
            )
        
        # Generate section results if enabled
        if section_results_enabled and section_questions:
            section_pdf_path = pdf_generator.generate_section_results_report(
                analysis_results,
                filename=f"test_{test_id}_sections",
                section_questions=section_questions
            )
            
            with open(section_pdf_path, 'rb') as pdf_file:
                await application.bot.send_document(
                    chat_id=teacher_id,
                    document=pdf_file,
                    filename=f"{test['name']}_section_results.pdf",
                    caption="📋 Bo'limlar bo'yicha natijalar"
                )
        
        logger.info(f"Test {test_id} natijalari o'qituvchi {teacher_id} ga yuborildi")
        
    except Exception as e:
        logger.error(f"Test {test_id} tahlilida xatolik: {e}")
        await application.bot.send_message(
            chat_id=teacher_id,
            text=f"❌ Test tahlilida xatolik yuz berdi:\n\n{str(e)}\n\n"
                 f"Iltimos, test natijalarini tekshiring.",
            parse_mode='Markdown'
        )
