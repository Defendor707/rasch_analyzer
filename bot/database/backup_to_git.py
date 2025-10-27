"""
Database ma'lumotlarini Git ga backup qilish
Bu script ma'lum vaqt oralig'ida yoki manual ravishda database ni JSON formatda export qiladi
va Git ga commit qiladi
"""
import asyncio
import json
import os
import logging
from datetime import datetime
from sqlalchemy import select
from bot.database.connection import db
from bot.database.schema import (
    User, Student, Test, TestResult, Payment, PaymentConfig, SystemLog
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Database backup manager"""
    
    def __init__(self, backup_dir: str = 'data/backups'):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def get_backup_filename(self, table_name: str) -> str:
        """Backup fayl nomini yaratish"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(self.backup_dir, f"{table_name}_{timestamp}.json")
    
    def get_latest_backup_filename(self, table_name: str) -> str:
        """Oxirgi backup fayl nomi"""
        return os.path.join(self.backup_dir, f"{table_name}_latest.json")
    
    async def backup_users(self, session):
        """Foydalanuvchilarni backup qilish"""
        logger.info("Users backup qilinmoqda...")
        
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        users_data = []
        for user in users:
            users_data.append({
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language': user.language,
                'preferences': user.preferences,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            })
        
        # Backup faylga yozish
        filename = self.get_latest_backup_filename('users')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(users_data)} ta user backup qilindi: {filename}")
        return len(users_data)
    
    async def backup_students(self, session):
        """Talabgorlarni backup qilish"""
        logger.info("Students backup qilinmoqda...")
        
        result = await session.execute(select(Student))
        students = result.scalars().all()
        
        students_data = []
        for student in students:
            students_data.append({
                'telegram_id': student.telegram_id,
                'teacher_id': student.teacher_id,
                'full_name': student.full_name,
                'phone': student.phone,
                'extra_data': student.extra_data,
                'created_at': student.created_at.isoformat() if student.created_at else None
            })
        
        filename = self.get_latest_backup_filename('students')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(students_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(students_data)} ta student backup qilindi: {filename}")
        return len(students_data)
    
    async def backup_tests(self, session):
        """Testlarni backup qilish"""
        logger.info("Tests backup qilinmoqda...")
        
        result = await session.execute(select(Test))
        tests = result.scalars().all()
        
        tests_data = []
        for test in tests:
            tests_data.append({
                'test_id': test.test_id,
                'teacher_id': test.teacher_id,
                'title': test.title,
                'total_questions': test.total_questions,
                'time_limit': test.time_limit,
                'has_sections': test.has_sections,
                'pdf_file_path': test.pdf_file_path,
                'answers': test.answers,
                'sections': test.sections,
                'is_active': test.is_active,
                'created_at': test.created_at.isoformat() if test.created_at else None,
                'updated_at': test.updated_at.isoformat() if test.updated_at else None
            })
        
        filename = self.get_latest_backup_filename('tests')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tests_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(tests_data)} ta test backup qilindi: {filename}")
        return len(tests_data)
    
    async def backup_test_results(self, session):
        """Test natijalarini backup qilish"""
        logger.info("Test results backup qilinmoqda...")
        
        result = await session.execute(select(TestResult))
        results = result.scalars().all()
        
        results_data = []
        for res in results:
            results_data.append({
                'test_id': res.test_id,
                'student_id': res.student_id,
                'teacher_id': res.teacher_id,
                'answers': res.answers,
                'score': res.score,
                'total_questions': res.total_questions,
                'started_at': res.started_at.isoformat() if res.started_at else None,
                'completed_at': res.completed_at.isoformat() if res.completed_at else None,
                'time_spent': res.time_spent,
                'is_completed': res.is_completed,
                'created_at': res.created_at.isoformat() if res.created_at else None
            })
        
        filename = self.get_latest_backup_filename('test_results')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(results_data)} ta natija backup qilindi: {filename}")
        return len(results_data)
    
    async def backup_payments(self, session):
        """To'lovlarni backup qilish"""
        logger.info("Payments backup qilinmoqda...")
        
        result = await session.execute(select(Payment))
        payments = result.scalars().all()
        
        payments_data = []
        for payment in payments:
            payments_data.append({
                'user_id': payment.user_id,
                'telegram_payment_charge_id': payment.telegram_payment_charge_id,
                'provider_payment_charge_id': payment.provider_payment_charge_id,
                'amount': payment.amount,
                'currency': payment.currency,
                'status': payment.status,
                'description': payment.description,
                'extra_data': payment.extra_data,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None
            })
        
        filename = self.get_latest_backup_filename('payments')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(payments_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(payments_data)} ta to'lov backup qilindi: {filename}")
        return len(payments_data)
    
    async def backup_payment_config(self, session):
        """To'lov sozlamalarini backup qilish"""
        logger.info("Payment config backup qilinmoqda...")
        
        result = await session.execute(select(PaymentConfig))
        configs = result.scalars().all()
        
        config_data = {}
        for config in configs:
            config_data[config.key] = config.value
        
        filename = self.get_latest_backup_filename('payment_config')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Payment config backup qilindi: {filename}")
        return len(config_data)
    
    async def run_full_backup(self):
        """To'liq backup qilish"""
        logger.info("=" * 60)
        logger.info(f"Database backup boshlandi: {datetime.now()}")
        logger.info("=" * 60)
        
        await db.initialize()
        
        async with db.get_session() as session:
            users_count = await self.backup_users(session)
            students_count = await self.backup_students(session)
            tests_count = await self.backup_tests(session)
            results_count = await self.backup_test_results(session)
            payments_count = await self.backup_payments(session)
            config_count = await self.backup_payment_config(session)
        
        logger.info("\n" + "=" * 60)
        logger.info("Backup tugadi!")
        logger.info(f"  - {users_count} ta foydalanuvchi")
        logger.info(f"  - {students_count} ta talabgor")
        logger.info(f"  - {tests_count} ta test")
        logger.info(f"  - {results_count} ta natija")
        logger.info(f"  - {payments_count} ta to'lov")
        logger.info(f"  - {config_count} ta config")
        logger.info(f"\nBackup papkasi: {self.backup_dir}")
        logger.info("=" * 60)
        
        await db.close()
        
        return {
            'users': users_count,
            'students': students_count,
            'tests': tests_count,
            'results': results_count,
            'payments': payments_count,
            'config': config_count
        }


async def main():
    """Backup scriptni ishga tushirish"""
    backup = DatabaseBackup()
    await backup.run_full_backup()
    
    logger.info("\nQo'shimcha: Replit avtomatik Git commit qiladi.")
    logger.info("Shuning uchun backup fayllari avtomatik tarzda Git ga saqlanadi.")


if __name__ == '__main__':
    asyncio.run(main())
