"""
To'liq test yaratish va sertifikat yuborish jarayonini simulatsiya qilish
"""
import asyncio
import logging
from datetime import datetime, timedelta
from bot.database.connection import db
from bot.database.managers import TestManager, TestResultManager, UserManager, StudentManager
from bot.utils.test_scheduler import process_and_send_test_results
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_test_simulation():
    """
    Test yaratish va talabalar javoblarini saqlash
    """
    try:
        await db.initialize()
        
        test_manager = TestManager()
        result_manager = TestResultManager()
        user_manager = UserManager()
        student_manager = StudentManager()
        
        # O'qituvchi yaratish
        teacher_id = 123456789
        await user_manager.create_or_update_user(
            telegram_id=str(teacher_id),
            username="teacher_demo",
            first_name="O'qituvchi",
            last_name="Demo"
        )
        logger.info(f"O'qituvchi yaratildi: {teacher_id}")
        
        # Talabalar yaratish
        students = [
            {'id': 111111111, 'name': 'Talabgor 1'},
            {'id': 222222222, 'name': 'Talabgor 2'},
            {'id': 333333333, 'name': 'Talabgor 3'},
        ]
        
        for student in students:
            await student_manager.add_student(
                telegram_id=str(student['id']),
                teacher_id=str(teacher_id),
                full_name=student['name']
            )
            logger.info(f"Talabgor yaratildi: {student['name']}")
        
        # Test yaratish
        import uuid
        test_id = f"test_{str(uuid.uuid4())[:8]}"
        test_title = 'Demo Matematika Testi'
        test_subject = 'Matematika'
        total_questions = 10
        
        # Javoblar dict formatida (question_number -> answer)
        answers_dict = {str(i+1): answer for i, answer in enumerate(['a', 'b', 'c', 'd', 'a', 'b', 'c', 'd', 'a', 'b'])}
        
        await test_manager.create_test(
            test_id=test_id,
            teacher_id=str(teacher_id),
            title=test_title,
            total_questions=total_questions,
            answers=answers_dict
        )
        
        logger.info(f"Test yaratildi: {test_id}")
        
        # Talabalarning javoblarini saqlash
        student_answers = [
            {'student': students[0], 'answers': {str(i+1): ans for i, ans in enumerate(['a', 'b', 'c', 'd', 'a', 'b', 'c', 'd', 'a', 'b'])}, 'score': 10},
            {'student': students[1], 'answers': {str(i+1): ans for i, ans in enumerate(['a', 'b', 'c', 'd', 'a', 'b', 'c', 'd', 'a', 'c'])}, 'score': 9},
            {'student': students[2], 'answers': {str(i+1): ans for i, ans in enumerate(['a', 'b', 'c', 'd', 'a', 'b', 'c', 'a', 'a', 'c'])}, 'score': 8},
        ]
        
        for item in student_answers:
            student = item['student']
            answers = item['answers']
            
            # Javoblarni saqlash (avval yaratish, keyin yangilash)
            result = await result_manager.create_result(
                test_id=test_id,
                student_id=str(student['id']),
                teacher_id=str(teacher_id),
                answers=answers
            )
            
            # Natijani yangilash (to'ldirilgan deb belgilash)
            await result_manager.update_result(
                result_id=result.id,
                score=float(item['score']),
                is_completed=True,
                completed_at=datetime.now()
            )
            
            logger.info(f"{student['name']} javoblari saqlandi: {item['score']}/10")
        
        # Test yakunlash
        await test_manager.finalize_test(test_id)
        logger.info("Test yakunlandi")
        
        return {
            'test_id': test_id,
            'teacher_id': teacher_id,
            'students': students,
            'test_title': test_title
        }
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        import traceback
        traceback.print_exc()
        return None


async def check_certificate_sending():
    """
    Sertifikatlar yuborilishini tekshirish
    """
    try:
        logger.info("\n" + "="*50)
        logger.info("SERTIFIKAT YUBORISH JARAYONINI TEKSHIRISH")
        logger.info("="*50 + "\n")
        
        # Test yaratish va ma'lumotlarni to'ldirish
        test_data = await create_test_simulation()
        
        if not test_data:
            logger.error("Test yaratilmadi!")
            return
        
        logger.info(f"\n✅ Test ID: {test_data['test_id']}")
        logger.info(f"✅ O'qituvchi ID: {test_data['teacher_id']}")
        logger.info(f"✅ Talabalar soni: {len(test_data['students'])}\n")
        
        # Endi bot orqali sertifikat yuborish jarayonini tekshirish
        # Bu qism botlar ishga tushganda avtomatik ishlaydi
        logger.info("⚠️  MUHIM:")
        logger.info("1. Sertifikatlar test muddati tugagach avtomatik yuboriladi")
        logger.info("2. Scheduler har soatda tekshiradi")
        logger.info("3. Test muddati 5 daqiqaga o'rnatilgan")
        logger.info("4. Yoki test_scheduler funksiyasini qo'lda chaqirish mumkin\n")
        
        # Ma'lumotlar bazasidagi natijalarni ko'rsatish
        async with db.get_session() as session:
            from sqlalchemy import select, text
            from bot.database.schema import TestResult
            
            result = await session.execute(
                select(TestResult).where(TestResult.test_id == test_data['test_id'])
            )
            results = list(result.scalars().all())
            
            logger.info(f"Database da saqlangan natijalar: {len(results)} ta")
            for r in results:
                logger.info(f"  - Talabgor {r.student_id}: {r.score}/{r.total_questions} ball, Tugallangan: {r.is_completed}")
        
        logger.info("\n" + "="*50)
        logger.info("✅ TEST MA'LUMOTLARI TAYYOR")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


if __name__ == '__main__':
    asyncio.run(check_certificate_sending())
