# 📁 Deployment Fayllari

Bu papkada Oracle VM'ga deploy qilish uchun barcha kerakli fayllar joylashgan.

## 📄 Fayllar Ro'yxati

### Asosiy Deployment Fayllari

1. **deploy.sh** - Avtomatik deployment scripti
   - Docker o'rnatish
   - Database yaratish
   - Container'larni ishga tushirish
   - Systemd service sozlash

2. **QUICK_START.md** - Tezkor boshlash qo'llanmasi (5-10 daqiqa)
   - Eng muhim komandalar
   - Qisqa va sodda

3. **ORACLE_DEPLOYMENT_GUIDE.md** - To'liq qo'llanma
   - Bosqichma-bosqich yo'riqnoma
   - Firewall sozlamalari
   - SSL sertifikat olish
   - Muammolarni hal qilish

### Backup va Restore

4. **backup.sh** - Database va data fayllarni backup qilish
5. **restore.sh** - Backup'dan tiklash
6. **cron_backup.sh** - Cron job uchun wrapper script
7. **setup_cron.sh** - Avtomatik kundalik backup sozlash

### Server Konfiguratsiyasi

8. **nginx.conf** - Nginx reverse proxy sozlamalari
9. **rasch-bot.service** - Systemd service fayli

## 🚀 Tezkor Ishga Tushirish

```bash
# 1. Loyihani VM'ga yuklash
scp -i key.pem -r /path/to/rasch-bot opc@VM_IP:/tmp/
ssh -i key.pem opc@VM_IP
sudo mv /tmp/rasch-bot /opt/

# 2. Environment sozlash
cd /opt/rasch-bot
sudo nano .env  # Bot tokenlarni kiriting

# 3. Deploy qilish
sudo ./deploy/deploy.sh

# 4. Tekshirish
docker-compose ps
docker-compose logs -f
```

## 📖 Qaysi Qo'llanmani O'qish Kerak?

- **Yangi boshlovchilar**: `QUICK_START.md` ni o'qing
- **Batafsil ma'lumot**: `ORACLE_DEPLOYMENT_GUIDE.md` ni o'qing
- **Muammolar**: `ORACLE_DEPLOYMENT_GUIDE.md` ning "Troubleshooting" bo'limiga qarang

## 🔄 Backup Strategiyasi

### Qo'lda Backup

```bash
sudo /opt/rasch-bot/deploy/backup.sh
```

### Avtomatik Backup (Kundalik)

```bash
sudo /opt/rasch-bot/deploy/setup_cron.sh
```

Bu cron job'ni sozlaydi va har kuni ertalab soat 03:00 da avtomatik backup oladi.

### Restore

```bash
sudo /opt/rasch-bot/deploy/restore.sh
```

Script sizdan backup fayl yo'lini so'raydi.

## 📋 Deployment Checklist

Deploy qilishdan oldin tekshiring:

- [ ] Oracle VM yaratildi
- [ ] SSH ulanishi ishlayapti
- [ ] Bot tokenlar tayyor
- [ ] PostgreSQL parol o'ylandi
- [ ] Firewall portlari ochildi (80, 443, 5432)
- [ ] .env fayli to'ldirildi
- [ ] deploy.sh scriptiga execute ruxsati berildi

## 🛠️ Foydali Komandalar

```bash
# Container statusini ko'rish
docker-compose ps

# Loglarni ko'rish
docker-compose logs -f

# Qayta ishga tushirish
docker-compose restart

# To'xtatish
docker-compose down

# Ishga tushirish
docker-compose up -d

# Backup olish
sudo ./deploy/backup.sh

# Database'ga ulanish
docker-compose exec postgres psql -U rasch_user -d rasch_bot
```

## 🔒 Xavfsizlik

- Bot tokenlarni hech qachon Git'ga commit qilmang
- Kuchli parollar ishlating
- Muntazam backup oling
- Tizimni yangilab turing

---

**Yordam kerakmi?** To'liq qo'llanmani o'qing: `ORACLE_DEPLOYMENT_GUIDE.md`
