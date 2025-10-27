"""
JSON fayllardan PostgreSQL ga ma'lumotlarni ko'chirish
Bu script bir marta ishlatiladi - JSON fayllardan PostgreSQL ga o'tish uchun
"""
import asyncio
import json
import os
import logging
from datetime import datetime
from sqlalchemy import select
from bot.database.connection import db
from bot.database.schema import (
    User, Student, Test, TestResult, Payment, PaymentConfig
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JSONToPostgresMigration:
    """JSON fayllardan PostgreSQL ga migratsiya"""
    
    def __init__(self):
        self.data_dir = 'data'
        self.backup_dir = 'data/backup_before_migration'
        
    def ensure_backup_dir(self):
        """Backup papkasini yaratish"""
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def load_json_file(self, filename: str):
        """JSON faylni yuklash"""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"{filename} topilmadi, bo'sh dict qaytariladi")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"{filename} o'qishda xatolik: {e}")
            return {}
    
    def backup_json_file(self, filename: str):
        """JSON faylni backup qilish"""
        src = os.path.join(self.data_dir, filename)
        if not os.path.exists(src):
            return
            
        dst = os.path.join(self.backup_dir, filename)
        try:
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"{filename} backup qilindi -> {dst}")
        except Exception as e:
            logger.error(f"{filename} backup qilishda xatolik: {e}")
    
    async def migrate_users(self, session):
        """User profiles ni migratsiya qilish"""
        logger.info("Foydalanuvchilar migratsiya qilinmoqda...")
        
        user_profiles = self.load_json_file('user_profiles.json')
        migrated_count = 0
        
        for telegram_id, profile in user_profiles.items():
            try:
                # Mavjudligini tekshirish
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info(f"User {telegram_id} allaqachon mavjud, o'tkazib yuborildi")
                    continue
                
                user = User(
                    telegram_id=telegram_id,
                    username=profile.get('username'),
                    first_name=profile.get('first_name'),
                    last_name=profile.get('last_name'),
                    language=profile.get('language', 'uz'),
                    preferences=profile
                )
                session.add(user)
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"User {telegram_id} migratsiya qilishda xatolik: {e}")
        
        await session.commit()
        logger.info(f"{migrated_count} ta foydalanuvchi migratsiya qilindi")
        return migrated_count
    
    async def migrate_students(self, session):
        """Talabgorlarni migratsiya qilish"""
        logger.info("Talabgorlar migratsiya qilinmoqda...")
        
        students_data = self.load_json_file('students.json')
        migrated_count = 0
        
        for teacher_id, students in students_data.items():
            if not isinstance(students, list):
                continue
                
            for student_info in students:
                try:
                    telegram_id = student_info.get('telegram_id')
                    if not telegram_id:
                        continue
                    
                    # Mavjudligini tekshirish
                    result = await session.execute(
                        select(Student).where(Student.telegram_id == telegram_id)
                    )
                    existing_student = result.scalar_one_or_none()
                    
                    if existing_student:
                        continue
                    
                    student = Student(
                        telegram_id=telegram_id,
                        teacher_id=teacher_id,
                        full_name=student_info.get('full_name', 'N/A'),
                        phone=student_info.get('phone'),
                        extra_data=student_info
                    )
                    session.add(student)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Student migratsiya qilishda xatolik: {e}")
        
        await session.commit()
        logger.info(f"{migrated_count} ta talabgor migratsiya qilindi")
        return migrated_count
    
    async def migrate_tests(self, session):
        """Testlarni migratsiya qilish"""
        logger.info("Testlar migratsiya qilinmoqda...")
        
        tests_data = self.load_json_file('tests.json')
        migrated_count = 0
        
        for test_id, test_info in tests_data.items():
            try:
                # Mavjudligini tekshirish
                result = await session.execute(
                    select(Test).where(Test.test_id == test_id)
                )
                existing_test = result.scalar_one_or_none()
                
                if existing_test:
                    continue
                
                test = Test(
                    test_id=test_id,
                    teacher_id=test_info.get('teacher_id', ''),
                    title=test_info.get('title', 'Nomsiz test'),
                    total_questions=test_info.get('total_questions', 0),
                    time_limit=test_info.get('time_limit'),
                    has_sections=test_info.get('has_sections', False),
                    pdf_file_path=test_info.get('pdf_file_path'),
                    answers=test_info.get('answers', {}),
                    sections=test_info.get('sections'),
                    is_active=test_info.get('is_active', True)
                )
                session.add(test)
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"Test {test_id} migratsiya qilishda xatolik: {e}")
        
        await session.commit()
        logger.info(f"{migrated_count} ta test migratsiya qilindi")
        return migrated_count
    
    async def migrate_payments(self, session):
        """To'lovlarni migratsiya qilish"""
        logger.info("To'lovlar migratsiya qilinmoqda...")
        
        payments_data = self.load_json_file('payments.json')
        migrated_count = 0
        
        for payment_id, payment_info in payments_data.items():
            try:
                charge_id = payment_info.get('telegram_payment_charge_id')
                if not charge_id:
                    continue
                
                # Mavjudligini tekshirish
                result = await session.execute(
                    select(Payment).where(Payment.telegram_payment_charge_id == charge_id)
                )
                existing_payment = result.scalar_one_or_none()
                
                if existing_payment:
                    continue
                
                payment = Payment(
                    user_id=payment_info.get('user_id', ''),
                    telegram_payment_charge_id=charge_id,
                    provider_payment_charge_id=payment_info.get('provider_payment_charge_id'),
                    amount=payment_info.get('amount', 0),
                    currency=payment_info.get('currency', 'XTR'),
                    status=payment_info.get('status', 'completed'),
                    description=payment_info.get('description'),
                    extra_data=payment_info
                )
                session.add(payment)
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"Payment migratsiya qilishda xatolik: {e}")
        
        await session.commit()
        logger.info(f"{migrated_count} ta to'lov migratsiya qilindi")
        return migrated_count
    
    async def migrate_payment_config(self, session):
        """To'lov sozlamalarini migratsiya qilish"""
        logger.info("To'lov sozlamalari migratsiya qilinmoqda...")
        
        config_data = self.load_json_file('payment_config.json')
        
        for key, value in config_data.items():
            try:
                # Mavjudligini tekshirish
                result = await session.execute(
                    select(PaymentConfig).where(PaymentConfig.key == key)
                )
                existing_config = result.scalar_one_or_none()
                
                if existing_config:
                    existing_config.value = value
                else:
                    config = PaymentConfig(key=key, value=value)
                    session.add(config)
                    
            except Exception as e:
                logger.error(f"Config {key} migratsiya qilishda xatolik: {e}")
        
        await session.commit()
        logger.info("To'lov sozlamalari migratsiya qilindi")
    
    async def run_migration(self):
        """To'liq migratsiyani bajarish"""
        logger.info("=" * 60)
        logger.info("JSON dan PostgreSQL ga migratsiya boshlandi")
        logger.info("=" * 60)
        
        # Backup
        self.ensure_backup_dir()
        logger.info("\n1. JSON fayllarni backup qilish...")
        for filename in ['user_profiles.json', 'students.json', 'tests.json', 
                        'payments.json', 'payment_config.json']:
            self.backup_json_file(filename)
        
        # Database ni boshlash
        logger.info("\n2. Database ga ulanish...")
        await db.initialize()
        
        # Jadvallarni yaratish
        logger.info("\n3. Database jadvalarini yaratish...")
        await db.create_tables()
        
        # Migratsiya
        logger.info("\n4. Ma'lumotlarni migratsiya qilish...")
        async with db.get_session() as session:
            users_count = await self.migrate_users(session)
            students_count = await self.migrate_students(session)
            tests_count = await self.migrate_tests(session)
            payments_count = await self.migrate_payments(session)
            await self.migrate_payment_config(session)
        
        logger.info("\n" + "=" * 60)
        logger.info("Migratsiya tugadi!")
        logger.info(f"  - {users_count} ta foydalanuvchi")
        logger.info(f"  - {students_count} ta talabgor")
        logger.info(f"  - {tests_count} ta test")
        logger.info(f"  - {payments_count} ta to'lov")
        logger.info("=" * 60)
        
        # Database ni yopish
        await db.close()
        
        logger.info("\nJSON backup fayllari: data/backup_before_migration/")
        logger.info("Agar hamma narsa yaxshi bo'lsa, eski JSON fayllarni o'chirishingiz mumkin")


async def main():
    """Migration scriptni ishga tushirish"""
    migration = JSONToPostgresMigration()
    await migration.run_migration()


if __name__ == '__main__':
    asyncio.run(main())
