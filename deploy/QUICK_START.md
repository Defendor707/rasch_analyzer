# ⚡ Tezkor Boshlash Qo'llanmasi

Oracle VM'ga 10 daqiqada deploy qilish!

## 📋 Kerakli Narsalar

- Oracle VM Public IP: `_______________`
- SSH Key fayli: `_______________`
- Teacher Bot Token: `_______________`
- Student Bot Token: `_______________`

---

## 🚀 5 Oddiy Bosqich

### 1️⃣ SSH orqali ulanish

```bash
ssh -i your-key.pem opc@YOUR_VM_IP
```

### 2️⃣ Loyihani yuklash

**Variant A: SFTP bilan**
```bash
# Mahalliy kompyuterda
scp -i your-key.pem -r /path/to/rasch-bot opc@YOUR_VM_IP:/tmp/

# VM'da
sudo mv /tmp/rasch-bot /opt/
```

**Variant B: Git bilan**
```bash
cd /opt
sudo git clone YOUR_REPO_URL rasch-bot
```

### 3️⃣ Environment sozlash

```bash
cd /opt/rasch-bot
sudo nano .env
```

Quyidagilarni yozing:
```env
BOT_TOKEN=your_teacher_bot_token
STUDENT_BOT_TOKEN=your_student_bot_token
POSTGRES_PASSWORD=KuchliParol123!
POSTGRES_USER=rasch_user
POSTGRES_DB=rasch_bot
```

Saqlash: `CTRL+O`, `ENTER`, `CTRL+X`

### 4️⃣ Deploy qilish

```bash
cd /opt/rasch-bot
sudo chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

Script quyidagilarni avtomatik bajaradi:
- ✅ Docker o'rnatish
- ✅ Database yaratish
- ✅ Bot'larni ishga tushirish

### 5️⃣ Tekshirish

```bash
docker-compose ps
docker-compose logs -f
```

Bot'lar ishga tushdi? **Telegram'da /start yuboring!** 🎉

---

## 🔍 Tezkor Komandalar

```bash
# Loglarni ko'rish
docker-compose logs -f

# Qayta ishga tushirish
docker-compose restart

# To'xtatish
docker-compose down

# Ishga tushirish
docker-compose up -d

# Backup olish
sudo /opt/rasch-bot/deploy/backup.sh
```

---

## ❓ Muammo bo'lsa?

1. **Bot ishlamayapti?**
   ```bash
   docker-compose logs telegram_bots
   ```

2. **Database xatosi?**
   ```bash
   docker-compose ps postgres
   docker-compose logs postgres
   ```

3. **Port band?**
   ```bash
   sudo netstat -tlnp | grep 5432
   ```

---

## 📚 To'liq Qo'llanma

Batafsil ma'lumot uchun: **ORACLE_DEPLOYMENT_GUIDE.md**

---

**Omad! 🚀**
