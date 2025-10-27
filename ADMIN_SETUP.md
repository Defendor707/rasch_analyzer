# Admin va Error Alerting Tizimini Sozlash

## 1. Admin ID ni topish

Telegram'da o'z ID ingizni topish uchun:
1. Telegram'da `@userinfobot` botiga `/start` yuboring
2. Bot sizga ID ingizni ko'rsatadi (masalan: `123456789`)

## 2. Admin ID ni qo'shish

### Variant 1: Admin panel orqali
1. O'qituvchi botiga `/admos` buyrug'ini yuboring
2. Admin panelda "Admin IDs" sozlamalarini toping
3. O'z ID ingizni qo'shing

### Variant 2: payment_config.json faylini tahrirlash
1. `data/payment_config.json` faylini oching
2. `admin_ids` qatoriga o'z ID ingizni qo'shing:
```json
{
  "analysis_price_stars": 1,
  "currency": "XTR",
  "admin_ids": [123456789],
  "payment_enabled": false
}
```

## 3. Error Alerting qanday ishlaydi?

- Bot ichida xatolik yuz berganda, barcha adminlarga Telegram orqali xabar yuboriladi
- Xabarda quyidagi ma'lumotlar bo'ladi:
  - Xatolik vaqti
  - Xatolik turi
  - Foydalanuvchi ma'lumotlari
  - Xatolik matni va traceback

## 4. Test qilish

1. Botni ishga tushiring
2. Biror xatolik yuzaga kelganda, sizga Telegram orqali xabar keladi
3. Agar xabar kelmasa, Admin ID to'g'ri kiritilganligini tekshiring

## 5. Muhim xabarnomalar

Admin `notify_critical` funksiyasi orqali muhim hodisalar haqida ham xabar olishi mumkin:

```python
from bot.utils.error_notifier import error_notifier

await error_notifier.notify_critical(
    context=context,
    message="Database backup muvaffaqiyatli amalga oshirildi"
)
```
