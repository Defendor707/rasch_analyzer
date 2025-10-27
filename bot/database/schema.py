"""
PostgreSQL Database Schema
Bu fayl barcha database jadvallarini aniqlaydi
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Foydalanuvchi ma'lumotlari (o'qituvchilar)"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language = Column(String(10), default='uz')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Qo'shimcha sozlamalar
    preferences = Column(JSON, default={})


class Student(Base):
    """Talabgorlar ma'lumotlari"""
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    teacher_id = Column(String(50), nullable=False, index=True)  # O'qituvchi telegram ID
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Qo'shimcha ma'lumotlar
    extra_data = Column(JSON, default={})


class Test(Base):
    """Testlar ma'lumotlari"""
    __tablename__ = 'tests'
    
    id = Column(Integer, primary_key=True)
    test_id = Column(String(100), unique=True, nullable=False, index=True)
    teacher_id = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    
    # Test konfiguratsiyasi
    total_questions = Column(Integer, nullable=False)
    time_limit = Column(Integer)  # Daqiqalarda
    has_sections = Column(Boolean, default=False)
    
    # PDF fayl
    pdf_file_path = Column(String(500))
    
    # Savol va javoblar
    answers = Column(JSON, nullable=False)  # To'g'ri javoblar
    sections = Column(JSON)  # Bo'limlar ma'lumotlari
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TestResult(Base):
    """Test natijalari"""
    __tablename__ = 'test_results'
    
    id = Column(Integer, primary_key=True)
    test_id = Column(String(100), ForeignKey('tests.test_id'), nullable=False, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    teacher_id = Column(String(50), nullable=False, index=True)
    
    # Javoblar
    answers = Column(JSON, nullable=False)
    score = Column(Float)
    total_questions = Column(Integer)
    
    # Vaqt
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    time_spent = Column(Integer)  # Soniyalarda
    
    # Holat
    is_completed = Column(Boolean, default=False)
    results_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    """To'lovlar tarixi"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    telegram_payment_charge_id = Column(String(200), unique=True)
    provider_payment_charge_id = Column(String(200))
    
    # To'lov ma'lumotlari
    amount = Column(Integer, nullable=False)  # Telegram Stars
    currency = Column(String(10), default='XTR')
    
    # Status
    status = Column(String(20), default='pending')  # pending, completed, failed
    
    # Qo'shimcha
    description = Column(Text)
    extra_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class PaymentConfig(Base):
    """To'lov sozlamalari"""
    __tablename__ = 'payment_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())


class SystemLog(Base):
    """Tizim loglari va xatoliklar"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    log_type = Column(String(50), nullable=False, index=True)  # error, warning, info
    message = Column(Text, nullable=False)
    user_id = Column(String(50), index=True)
    traceback = Column(Text)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
