"""
PostgreSQL uchun Database Managers
Barcha database operatsiyalari uchun yagona interface
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.exc import IntegrityError
from bot.database.connection import db
from bot.database.schema import (
    User, Student, Test, TestResult, Payment, PaymentConfig, SystemLog
)

logger = logging.getLogger(__name__)


class UserManager:
    """Foydalanuvchilar bilan ishlash"""
    
    @staticmethod
    async def create_or_update_user(
        telegram_id: str,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        language: str = 'uz',
        preferences: dict = None
    ) -> User:
        """Foydalanuvchi yaratish yoki yangilash"""
        async with db.get_session() as session:
            # Mavjudligini tekshirish
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Yangilash
                user.username = username or user.username
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.language = language
                if preferences:
                    user.preferences = preferences
            else:
                # Yaratish
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language=language,
                    preferences=preferences or {}
                )
                session.add(user)
            
            await session.commit()
            await session.refresh(user)
            return user
    
    @staticmethod
    async def get_user(telegram_id: str) -> Optional[User]:
        """Foydalanuvchini olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_preferences(telegram_id: str) -> dict:
        """Foydalanuvchi sozlamalarini olish"""
        user = await UserManager.get_user(telegram_id)
        return user.preferences if user else {}
    
    @staticmethod
    async def update_preferences(telegram_id: str, preferences: dict):
        """Sozlamalarni yangilash"""
        async with db.get_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(preferences=preferences)
            )
            await session.commit()


class StudentManager:
    """Talabgorlar bilan ishlash"""
    
    @staticmethod
    async def add_student(
        telegram_id: str,
        teacher_id: str,
        full_name: str,
        phone: str = None,
        extra_data: dict = None
    ) -> Student:
        """Yangi talabgor qo'shish"""
        async with db.get_session() as session:
            # Mavjudligini tekshirish
            result = await session.execute(
                select(Student).where(Student.telegram_id == telegram_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Yangilash
                existing.full_name = full_name
                existing.phone = phone
                if extra_data:
                    existing.extra_data = extra_data
                student = existing
            else:
                student = Student(
                    telegram_id=telegram_id,
                    teacher_id=teacher_id,
                    full_name=full_name,
                    phone=phone,
                    extra_data=extra_data or {}
                )
                session.add(student)
            
            await session.commit()
            await session.refresh(student)
            return student
    
    @staticmethod
    async def get_students_by_teacher(teacher_id: str) -> List[Student]:
        """O'qituvchining talabgorlarini olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(Student).where(Student.teacher_id == teacher_id)
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def get_student(telegram_id: str) -> Optional[Student]:
        """Talabgorni olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(Student).where(Student.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_student(telegram_id: str):
        """Talabgorni o'chirish"""
        async with db.get_session() as session:
            await session.execute(
                delete(Student).where(Student.telegram_id == telegram_id)
            )
            await session.commit()


class TestManager:
    """Testlar bilan ishlash"""
    
    @staticmethod
    async def create_test(
        test_id: str,
        teacher_id: str,
        title: str,
        total_questions: int,
        answers: dict,
        time_limit: int = None,
        has_sections: bool = False,
        sections: dict = None,
        pdf_file_path: str = None
    ) -> Test:
        """Yangi test yaratish"""
        async with db.get_session() as session:
            test = Test(
                test_id=test_id,
                teacher_id=teacher_id,
                title=title,
                total_questions=total_questions,
                time_limit=time_limit,
                has_sections=has_sections,
                pdf_file_path=pdf_file_path,
                answers=answers,
                sections=sections,
                is_active=True
            )
            session.add(test)
            await session.commit()
            await session.refresh(test)
            return test
    
    @staticmethod
    async def get_test(test_id: str) -> Optional[Test]:
        """Testni olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(Test).where(Test.test_id == test_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tests_by_teacher(teacher_id: str) -> List[Test]:
        """O'qituvchining testlarini olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(Test)
                .where(and_(Test.teacher_id == teacher_id, Test.is_active == True))
                .order_by(Test.created_at.desc())
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def update_test(test_id: str, **kwargs):
        """Testni yangilash"""
        async with db.get_session() as session:
            await session.execute(
                update(Test)
                .where(Test.test_id == test_id)
                .values(**kwargs)
            )
            await session.commit()
    
    @staticmethod
    async def delete_test(test_id: str):
        """Testni o'chirish (is_active=False qilish)"""
        await TestManager.update_test(test_id, is_active=False)


class TestResultManager:
    """Test natijalari bilan ishlash"""
    
    @staticmethod
    async def create_result(
        test_id: str,
        student_id: str,
        teacher_id: str,
        answers: dict,
        started_at: datetime = None
    ) -> TestResult:
        """Yangi natija yaratish"""
        async with db.get_session() as session:
            result = TestResult(
                test_id=test_id,
                student_id=student_id,
                teacher_id=teacher_id,
                answers=answers,
                started_at=started_at or datetime.now(),
                is_completed=False
            )
            session.add(result)
            await session.commit()
            await session.refresh(result)
            return result
    
    @staticmethod
    async def update_result(
        result_id: int,
        answers: dict = None,
        score: float = None,
        is_completed: bool = None,
        completed_at: datetime = None,
        time_spent: int = None
    ):
        """Natijani yangilash"""
        async with db.get_session() as session:
            values = {}
            if answers is not None:
                values['answers'] = answers
            if score is not None:
                values['score'] = score
            if is_completed is not None:
                values['is_completed'] = is_completed
            if completed_at is not None:
                values['completed_at'] = completed_at
            if time_spent is not None:
                values['time_spent'] = time_spent
            
            if values:
                await session.execute(
                    update(TestResult)
                    .where(TestResult.id == result_id)
                    .values(**values)
                )
                await session.commit()
    
    @staticmethod
    async def get_results_by_test(test_id: str) -> List[TestResult]:
        """Test bo'yicha natijalarni olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(TestResult)
                .where(TestResult.test_id == test_id)
                .order_by(TestResult.created_at.desc())
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def get_results_by_student(student_id: str) -> List[TestResult]:
        """Talabgor bo'yicha natijalarni olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(TestResult)
                .where(TestResult.student_id == student_id)
                .order_by(TestResult.created_at.desc())
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def check_results_sent(test_id: str) -> bool:
        """Test uchun natijalar yuborilgan yoki yo'qligini tekshirish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(TestResult)
                .where(TestResult.test_id == test_id)
                .where(TestResult.is_completed == True)
            )
            # Check if all results have results_sent field and it's True
            results = list(result.scalars().all())
            if not results:
                return False
            
            # Check each result for results_sent attribute
            for res in results:
                # If attribute doesn't exist or is False, consider as not sent
                if not hasattr(res, 'results_sent') or not res.results_sent:
                    return False
            return True


class PaymentManager:
    """To'lovlar bilan ishlash"""
    
    @staticmethod
    async def create_payment(
        user_id: str,
        amount: int,
        telegram_payment_charge_id: str = None,
        provider_payment_charge_id: str = None,
        status: str = 'pending',
        description: str = None,
        extra_data: dict = None
    ) -> Payment:
        """Yangi to'lov yaratish"""
        async with db.get_session() as session:
            payment = Payment(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                provider_payment_charge_id=provider_payment_charge_id,
                amount=amount,
                currency='XTR',
                status=status,
                description=description,
                extra_data=extra_data or {}
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            return payment
    
    @staticmethod
    async def update_payment_status(
        payment_id: int,
        status: str,
        completed_at: datetime = None
    ):
        """To'lov statusini yangilash"""
        async with db.get_session() as session:
            values = {'status': status}
            if completed_at:
                values['completed_at'] = completed_at
            
            await session.execute(
                update(Payment)
                .where(Payment.id == payment_id)
                .values(**values)
            )
            await session.commit()
    
    @staticmethod
    async def get_payments_by_user(user_id: str) -> List[Payment]:
        """Foydalanuvchi to'lovlarini olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(Payment)
                .where(Payment.user_id == user_id)
                .order_by(Payment.created_at.desc())
            )
            return list(result.scalars().all())
    
    @staticmethod
    async def get_config(key: str, default: Any = None) -> Any:
        """Konfiguratsiya qiymatini olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(PaymentConfig).where(PaymentConfig.key == key)
            )
            config = result.scalar_one_or_none()
            return config.value if config else default
    
    @staticmethod
    async def set_config(key: str, value: Any):
        """Konfiguratsiya qiymatini o'rnatish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(PaymentConfig).where(PaymentConfig.key == key)
            )
            config = result.scalar_one_or_none()
            
            if config:
                config.value = value
            else:
                config = PaymentConfig(key=key, value=value)
                session.add(config)
            
            await session.commit()


class SystemLogManager:
    """Tizim loglari bilan ishlash"""
    
    @staticmethod
    async def log_error(
        message: str,
        user_id: str = None,
        traceback: str = None,
        extra_data: dict = None
    ):
        """Xatolikni saqlash"""
        async with db.get_session() as session:
            log = SystemLog(
                log_type='error',
                message=message,
                user_id=user_id,
                traceback=traceback,
                extra_data=extra_data or {}
            )
            session.add(log)
            await session.commit()
    
    @staticmethod
    async def log_info(
        message: str,
        user_id: str = None,
        extra_data: dict = None
    ):
        """Ma'lumotni saqlash"""
        async with db.get_session() as session:
            log = SystemLog(
                log_type='info',
                message=message,
                user_id=user_id,
                extra_data=extra_data or {}
            )
            session.add(log)
            await session.commit()
    
    @staticmethod
    async def get_recent_errors(limit: int = 100) -> List[SystemLog]:
        """Oxirgi xatoliklarni olish"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SystemLog)
                .where(SystemLog.log_type == 'error')
                .order_by(SystemLog.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
