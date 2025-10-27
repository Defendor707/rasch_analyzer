# PostgreSQL Database Foydalanish Qo'llanmasi

## Tizim Haqida

Telegram bot endi ma'lumotlarni JSON fayllar o'rniga PostgreSQL database da saqlaydi. Bu yanada tez, ishonchli va kengaytiriladigan yechim.

---

## 1. Birinchi Marta Ishlatish

### 1.1. Database Migratsiya (JSON → PostgreSQL)

Eski JSON fayllardan PostgreSQL ga o'tish uchun:

```bash
python -m bot.database.migrate_json_to_postgres
```

Bu script:
- JSON fayllarni `data/backup_before_migration/` papkasiga backup qiladi
- PostgreSQL jadvallarini yaratadi
- Barcha ma'lumotlarni PostgreSQL ga ko'chiradi

### 1.2. To'g'ridan-to'g'ri Ishlatish

Agar siz yangi boshlanuvchi bo'lsangiz yoki JSON fayllar bo'lmasa:

```bash
# Database jadvallarini yaratish
python -c "import asyncio; from bot.database.connection import db; asyncio.run(db.initialize()); asyncio.run(db.create_tables())"
```

---

## 2. Database Managerlardan Foydalanish

### 2.1. Foydalanuvchilar (UserManager)

```python
from bot.database.managers import UserManager

# Foydalanuvchi yaratish yoki yangilash
user = await UserManager.create_or_update_user(
    telegram_id="123456789",
    username="johndoe",
    first_name="John",
    last_name="Doe",
    language="uz",
    preferences={"theme": "dark"}
)

# Foydalanuvchini olish
user = await UserManager.get_user("123456789")

# Sozlamalarni olish
prefs = await UserManager.get_user_preferences("123456789")
```

### 2.2. Talabgorlar (StudentManager)

```python
from bot.database.managers import StudentManager

# Talabgor qo'shish
student = await StudentManager.add_student(
    telegram_id="987654321",
    teacher_id="123456789",
    full_name="Ali Valiyev",
    phone="+998901234567"
)

# O'qituvchining talabgorlarini olish
students = await StudentManager.get_students_by_teacher("123456789")

# Talabgorni o'chirish
await StudentManager.delete_student("987654321")
```

### 2.3. Testlar (TestManager)

```python
from bot.database.managers import TestManager

# Test yaratish
test = await TestManager.create_test(
    test_id="test_123",
    teacher_id="123456789",
    title="Matematika Test",
    total_questions=50,
    answers={"1": "a", "2": "b", "3": "c"},
    time_limit=60,  # daqiqalarda
    has_sections=True,
    sections={"Math": [1, 2, 3]}
)

# Testni olish
test = await TestManager.get_test("test_123")

# O'qituvchining testlarini olish
tests = await TestManager.get_tests_by_teacher("123456789")
```

### 2.4. To'lovlar (PaymentManager)

```python
from bot.database.managers import PaymentManager

# To'lov yaratish
payment = await PaymentManager.create_payment(
    user_id="123456789",
    amount=100,
    status="completed",
    description="Rasch analiz"
)

# Foydalanuvchi to'lovlarini olish
payments = await PaymentManager.get_payments_by_user("123456789")

# Konfiguratsiya olish/o'rnatish
price = await PaymentManager.get_config("analysis_price_stars", default=1)
await PaymentManager.set_config("analysis_price_stars", 2)
```

---

## 3. Database Backup

### 3.1. Manual Backup

```bash
python -m bot.database.backup_to_git
```

Bu script:
- Barcha database ma'lumotlarini JSON formatda export qiladi
- `data/backups/` papkasiga saqlaydi
- Replit avtomatik tarzda Git ga commit qiladi

### 3.2. Avtomatik Backup

Backup ni APScheduler yoki cron job orqali avtomatlash mumkin:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.database.backup_to_git import DatabaseBackup

scheduler = AsyncIOScheduler()

async def run_backup():
    backup = DatabaseBackup()
    await backup.run_full_backup()

# Har kuni soat 02:00 da backup
scheduler.add_job(run_backup, 'cron', hour=2, minute=0)
scheduler.start()
```

---

## 4. Error Logging

Xatoliklarni database ga saqlash:

```python
from bot.database.managers import SystemLogManager

# Xatolikni saqlash
await SystemLogManager.log_error(
    message="Database connection failed",
    user_id="123456789",
    traceback=str(traceback.format_exc()),
    metadata={"error_code": 500}
)

# Ma'lumot saqlash
await SystemLogManager.log_info(
    message="User logged in",
    user_id="123456789"
)

# Oxirgi xatoliklarni olish
errors = await SystemLogManager.get_recent_errors(limit=50)
```

---

## 5. Database Health Check

```python
from bot.database.connection import db

# Database holatini tekshirish
is_healthy = await db.health_check()
if is_healthy:
    print("Database ishlayapti!")
else:
    print("Database bilan muammo bor!")
```

---

## 6. Muhim Eslatmalar

### ⚠️ Xavfsizlik
- Database ulanish ma'lumotlari environment variables da saqlanadi
- Hech qachon DATABASE_URL ni kod ichida hardcode qilmang
- Admin IDlarni `payment_config` da saqlang

### 💾 Backup
- Replit avtomatik Git backup qiladi
- Qo'shimcha backup uchun `backup_to_git.py` scriptini ishlating
- Backup fayllar `data/backups/` da saqlanadi

### 🔄 Migration
- Migration faqat bir marta ishlatiladi
- JSON fayllar `data/backup_before_migration/` da backup qilinadi
- Migration muvaffaqiyatli bo'lgandan keyin eski JSON fayllarni o'chirishingiz mumkin

### 🚀 Performance
- Database connection pool ishlatiladi
- Async operatsiyalar tezroq ishlaydi
- Indekslar muhim maydonlarga qo'yilgan (telegram_id, test_id, etc.)

---

## 7. Muammolarni Hal Qilish

### Database ulanmadi
```bash
# Environment variables ni tekshirish
env | grep DATABASE_URL
env | grep PGHOST
```

### Jadvallar yo'q
```bash
python -c "import asyncio; from bot.database.connection import db; asyncio.run(db.initialize()); asyncio.run(db.create_tables())"
```

### Ma'lumotlar yo'qoldi
```bash
# Backup dan qayta tiklash
# (Bu funksiya hali qo'shilmagan, lekin kerak bo'lsa qo'shish mumkin)
```

---

## 8. Keyingi Qadamlar

- ✅ PostgreSQL o'rnatildi
- ✅ Schema yaratildi
- ✅ Migration script tayyor
- ✅ Backup system tayyor
- ✅ Error alerting tizimi tayyor

**Hozir qilishingiz kerak:**
1. Migration scriptni ishlatib JSON → PostgreSQL ga o'tish
2. Bot kodlarini PostgreSQL managerlar bilan yangilash
3. Backup scriptni test qilish
4. Admin ID ni `payment_config.json` ga qo'shish (error notifications uchun)
