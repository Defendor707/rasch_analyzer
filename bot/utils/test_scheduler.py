import logging
import pandas as pd
from telegram.ext import Application
from typing import Optional
from .test_manager import TestManager
from .rasch_analysis import RaschAnalyzer
from .pdf_generator import PDFReportGenerator
from .user_data import UserDataManager

logger = logging.getLogger(__name__)


async def check_and_finalize_expired_tests(application: Application, student_bot_app: Application = None) -> None:
    """
    Check for expired tests and send analysis results to teachers
    
    Args:
        application: Telegram bot application instance (teacher bot)
        student_bot_app: Student bot application instance for sending certificates
    """
    test_manager = TestManager()
    expired_test_ids = test_manager.get_expired_tests()
    
    if not expired_test_ids:
        logger.info("Tugagan testlar topilmadi")
        return
    
    logger.info(f"Tugagan testlar topildi: {len(expired_test_ids)}")
    
    for test_id in expired_test_ids:
        try:
            await process_and_send_test_results(application, test_id, student_bot_app=student_bot_app)
        except Exception as e:
            logger.error(f"Test {test_id} natijalarini yuborishda xatolik: {e}")
            continue


async def send_certificate_to_student(application: Application, student_id: int, certificate_path: str, test_name: str) -> bool:
    """
    Send certificate to student via Telegram
    
    Args:
        application: Telegram bot application instance
        student_id: Student's Telegram ID
        certificate_path: Path to certificate PDF
        test_name: Name of the test
        
    Returns:
        Success status
    """
    try:
        with open(certificate_path, 'rb') as cert_file:
            await application.bot.send_document(
                chat_id=student_id,
                document=cert_file,
                filename=f"{test_name}_sertifikat.pdf",
                caption=f"🎓 <b>Tabriklaymiz!</b>\n\n"
                        f"<b>{test_name}</b> testi uchun sertifikatingiz tayyor.\n\n"
                        f"Natijalaringiz bilan tanishing va o'z darajangizni ko'ring!",
                parse_mode='HTML'
            )
        logger.info(f"Sertifikat yuborildi: {student_id}")
        return True
    except Exception as e:
        logger.error(f"Sertifikat yuborishda xatolik {student_id}: {e}")
        return False


async def send_test_results_to_students(test_id: str, student_bot_app: Application = None) -> dict:
    """
    Send test results to all students who completed the test (only once)
    
    Args:
        test_id: Test identifier
        student_bot_app: Student bot application instance for sending results
        
    Returns:
        Dictionary with success status and count of sent results
    """
    from bot.database.managers import TestResultManager
    
    if not student_bot_app:
        logger.error("Student bot application topilmadi")
        return {'success': False, 'count': 0, 'error': 'Student bot topilmadi'}
    
    test_manager = TestManager()
    result_manager = TestResultManager()
    
    # Get test info
    test = test_manager.get_test(test_id)
    if not test:
        logger.error(f"Test {test_id} topilmadi")
        return {'success': False, 'count': 0, 'error': 'Test topilmadi'}
    
    # Get all completed test results
    import asyncio
    from bot.database.connection import db
    from sqlalchemy import select, update
    from bot.database.schema import TestResult
    
    try:
        await db.initialize()
        
        async with db.get_session() as session:
            # Get results that haven't been sent yet
            result = await session.execute(
                select(TestResult)
                .where(TestResult.test_id == test_id)
                .where(TestResult.is_completed == True)
                .where(TestResult.results_sent == False)
            )
            unsent_results = list(result.scalars().all())
            
            if not unsent_results:
                logger.info(f"Test {test_id} uchun yuborilmagan natijalar yo'q")
                return {'success': True, 'count': 0, 'already_sent': True}
            
            sent_count = 0
            
            for test_result in unsent_results:
                try:
                    student_id = int(test_result.student_id)
                    score = test_result.score or 0
                    total = test_result.total_questions or 0
                    percentage = (score / total * 100) if total > 0 else 0
                    
                    # Determine grade
                    if percentage >= 90:
                        grade = "A (A'lo) 🥇"
                    elif percentage >= 80:
                        grade = "B (Yaxshi) 🥈"
                    elif percentage >= 70:
                        grade = "C (Qoniqarli) 🥉"
                    elif percentage >= 60:
                        grade = "D (O'rtacha) 📊"
                    else:
                        grade = "F (Qoniqarsiz) 📉"
                    
                    # Send result to student
                    message = (
                        f"📊 <b>Test natijalari</b>\n\n"
                        f"📋 Test: <b>{test['name']}</b>\n"
                        f"📚 Fan: <b>{test['subject']}</b>\n\n"
                        f"✅ To'g'ri javoblar: <b>{int(score)}/{total}</b>\n"
                        f"📈 Foiz: <b>{percentage:.1f}%</b>\n"
                        f"🎯 Baho: <b>{grade}</b>\n\n"
                        f"Test yakunlandi. Natijalaringiz yuqorida ko'rsatilgan."
                    )
                    
                    await student_bot_app.bot.send_message(
                        chat_id=student_id,
                        text=message,
                        parse_mode='HTML'
                    )
                    
                    # Mark as sent
                    await session.execute(
                        update(TestResult)
                        .where(TestResult.id == test_result.id)
                        .values(results_sent=True)
                    )
                    await session.commit()
                    
                    sent_count += 1
                    logger.info(f"Natija yuborildi: talabgor {student_id}, test {test_id}")
                    
                except Exception as student_error:
                    logger.error(f"Talabgor {test_result.student_id} ga natija yuborishda xatolik: {student_error}")
                    await session.rollback()
                    continue
            
            logger.info(f"Test {test_id} uchun {sent_count} ta natija yuborildi")
            return {'success': True, 'count': sent_count}
            
    except Exception as e:
        logger.error(f"Test natijalarini yuborishda xatolik: {e}")
        return {'success': False, 'count': 0, 'error': str(e)}


async def process_and_send_test_results(application: Application, test_id: str, student_bot_app: Application = None) -> None:
    """
    Process test results, perform Rasch analysis, and send to teacher
    Also sends certificates to all students
    
    Args:
        application: Telegram bot application instance (teacher bot)
        test_id: Test identifier
        student_bot_app: Student bot application instance for sending certificates
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
        
        # Generate general statistics report (umumiy statistika)
        general_pdf_path = pdf_generator.generate_report(
            analysis_results,
            filename=f"test_{test_id}_umumiy"
        )
        
        with open(general_pdf_path, 'rb') as pdf_file:
            await application.bot.send_document(
                chat_id=teacher_id,
                document=pdf_file,
                filename=f"{test['name']}_umumiy_statistika.pdf",
                caption="📊 Umumiy statistika va Wright Map"
            )
        
        # Generate person results report (talabgorlar natijalari)
        person_pdf_path = pdf_generator.generate_person_results_report(
            analysis_results,
            filename=f"test_{test_id}_talabgorlar",
            section_questions=section_questions if section_results_enabled else None
        )
        
        with open(person_pdf_path, 'rb') as pdf_file:
            await application.bot.send_document(
                chat_id=teacher_id,
                document=pdf_file,
                filename=f"{test['name']}_talabgorlar_natijalari.pdf",
                caption="👥 Talabgorlar natijalari"
            )
        
        # Generate section results if enabled
        if section_results_enabled and section_questions:
            section_pdf_path = pdf_generator.generate_section_results_report(
                analysis_results,
                filename=f"test_{test_id}_bulimlar",
                section_questions=section_questions
            )
            
            with open(section_pdf_path, 'rb') as pdf_file:
                await application.bot.send_document(
                    chat_id=teacher_id,
                    document=pdf_file,
                    filename=f"{test['name']}_bulimlar_natijalari.pdf",
                    caption="📋 Bo'limlar bo'yicha natijalar"
                )
        
        logger.info(f"Test {test_id} natijalari o'qituvchi {teacher_id} ga yuborildi")
        
        # Send certificates to all students
        await application.bot.send_message(
            chat_id=teacher_id,
            text="📜 Talabgorlarga sertifikatlar yuborilmoqda...",
            parse_mode='Markdown'
        )
        
        individual_results = analysis_results.get('person_statistics', {}).get('individual', [])
        student_ids = results_data.get('student_ids', [])
        
        certificates_sent = 0
        for idx, person_result in enumerate(individual_results):
            if idx < len(student_ids):
                student_id = student_ids[idx]
                
                # Get student's raw score from test results
                participants = test.get('participants', {})
                student_score_data = None
                
                if isinstance(participants, dict):
                    student_score_data = participants.get(str(student_id))
                elif isinstance(participants, list):
                    for p in participants:
                        if p.get('student_id') == student_id:
                            student_score_data = p
                            break
                
                if student_score_data:
                    score = student_score_data.get('score', 0)
                    max_score = student_score_data.get('max_score', n_questions)
                    percentage = student_score_data.get('percentage', 0)
                    
                    # Generate certificate
                    try:
                        cert_path = pdf_generator.generate_certificate(
                            student_name=f"Talabgor {student_id}",
                            test_name=test['name'],
                            subject=test['subject'],
                            score=score,
                            max_score=max_score,
                            percentage=percentage,
                            theta=person_result.get('ability', 0.0),
                            t_score=person_result.get('t_score', 50.0),
                            filename=f"cert_{test_id}_{student_id}"
                        )
                        
                        # Send certificate to student using student bot
                        if student_bot_app:
                            if await send_certificate_to_student(student_bot_app, student_id, cert_path, test['name']):
                                certificates_sent += 1
                        else:
                            logger.warning(f"Student bot application topilmadi, sertifikat yuborilmadi: {student_id}")
                    except Exception as cert_error:
                        logger.error(f"Talabgor {student_id} uchun sertifikat yaratishda xatolik: {cert_error}")
        
        # Notify teacher about certificates
        await application.bot.send_message(
            chat_id=teacher_id,
            text=f"✅ {certificates_sent} ta sertifikat talabgorlarga yuborildi!",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Test {test_id} tahlilida xatolik: {e}")
        await application.bot.send_message(
            chat_id=teacher_id,
            text=f"❌ Test tahlilida xatolik yuz berdi:\n\n{str(e)}\n\n"
                 f"Iltimos, test natijalarini tekshiring.",
            parse_mode='Markdown'
        )
