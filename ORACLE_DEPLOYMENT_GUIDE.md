# 🚀 Oracle VM'ga Rasch Bot Deployment Qo'llanmasi

Bu qo'llanma sizga Rasch Model Telegram Bot'ni Oracle Cloud VM instancega qanday deploy qilishni bosqichma-bosqich ko'rsatadi.

## 📋 Talablar

### Oracle VM Instance
- **OS**: Ubuntu 20.04/22.04 yoki Oracle Linux 8/9
- **RAM**: Kamida 2GB (4GB tavsiya etiladi)
- **Disk**: 20GB
- **Port**: 80, 443, 5432 (agar tashqi database kerak bo'lsa)

### Kerakli Ma'lumotlar
- ✅ Oracle VM Public IP manzili
- ✅ SSH private key fayli
- ✅ Telegram Bot tokenlar (Teacher va Student bot uchun)
- ✅ PostgreSQL parol

---

## 🔧 1-BOSQICH: Oracle VM'ga Ulanish

### SSH orqali ulanish:

```bash
# Private key faylini download qiling va ruxsatlarni o'rnating
chmod 400 /path/to/your-ssh-key.pem

# Oracle VM'ga ulanish (Oracle Linux uchun)
ssh -i /path/to/your-ssh-key.pem opc@YOUR_PUBLIC_IP

# yoki Ubuntu uchun
ssh -i /path/to/your-ssh-key.pem ubuntu@YOUR_PUBLIC_IP
```

**Eslatma**: `YOUR_PUBLIC_IP` ni Oracle Cloud Console'dan oling.

---

## 🔥 2-BOSQICH: Firewall Sozlamalari

### Oracle Cloud Console'da (Web interfeys)

1. **Navigation Menu** → **Networking** → **Virtual Cloud Networks**
2. Sizning VCN'ingizni tanlang
3. **Security Lists** → **Default Security List** ga o'ting
4. **Ingress Rules** bo'limida quyidagi portlarni qo'shing:

| Port | Protocol | Source CIDR | Description |
|------|----------|-------------|-------------|
| 22 | TCP | 0.0.0.0/0 | SSH |
| 80 | TCP | 0.0.0.0/0 | HTTP |
| 443 | TCP | 0.0.0.0/0 | HTTPS |
| 5432 | TCP | 0.0.0.0/0 | PostgreSQL (agar kerak bo'lsa) |

### VM ichida (Iptables/Firewalld)

```bash
# Oracle Linux uchun
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=5432/tcp
sudo firewall-cmd --reload

# Ubuntu uchun (UFW)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5432/tcp
sudo ufw enable
```

---

## 📦 3-BOSQICH: Loyiha Fayllarini Yuklash

### Variant 1: SFTP orqali yuklash (Tavsiya etiladi)

```bash
# Mahalliy kompyuteringizda (Linux/Mac)
scp -i /path/to/your-ssh-key.pem -r /path/to/rasch-bot opc@YOUR_PUBLIC_IP:/tmp/

# Windows uchun WinSCP yoki FileZilla ishlatishingiz mumkin
```

### Variant 2: Git orqali klonlash

```bash
# VM ichida
cd /opt
sudo git clone https://github.com/your-username/rasch-bot.git
```

### Variant 3: Zip fayl orqali

```bash
# Mahalliy kompyuterda loyihani zip qiling
cd /path/to/rasch-bot
zip -r rasch-bot.zip .

# VM'ga yuklash
scp -i /path/to/your-ssh-key.pem rasch-bot.zip opc@YOUR_PUBLIC_IP:/tmp/

# VM ichida
sudo mkdir -p /opt/rasch-bot
cd /opt/rasch-bot
sudo unzip /tmp/rasch-bot.zip
```

---

## ⚙️ 4-BOSQICH: Environment Sozlamalari

### .env faylini yaratish

```bash
cd /opt/rasch-bot
sudo nano .env
```

Quyidagi ma'lumotlarni kiriting:

```env
# Telegram Bot Tokens
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
STUDENT_BOT_TOKEN=9876543210:ZYXwvuTSRqponMLKjihgfeDCBA987654321

# PostgreSQL Database
POSTGRES_DB=rasch_bot
POSTGRES_USER=rasch_user
POSTGRES_PASSWORD=Kuchli_Parol_2024!

# Agar Oracle PostgreSQL ishlatmoqchi bo'lsangiz
# DATABASE_URL=postgresql://user:password@host:5432/database
```

**CTRL+O** (saqlash), **ENTER**, **CTRL+X** (chiqish)

---

## 🐳 5-BOSQICH: Deployment Scriptini Ishga Tushirish

```bash
cd /opt/rasch-bot

# Script'ga execute ruxsati bering
sudo chmod +x deploy/deploy.sh

# Deploy qilish
sudo ./deploy/deploy.sh
```

Bu script quyidagilarni avtomatik bajaradi:
1. ✅ Sistema yangilanishlarini o'rnatish
2. ✅ Docker va Docker Compose o'rnatish
3. ✅ Nginx o'rnatish
4. ✅ Loyiha papkalarini yaratish
5. ✅ Database yaratish va migratsiya
6. ✅ Container'larni ishga tushirish
7. ✅ Systemd service sozlash

---

## 🔍 6-BOSQICH: Tekshirish

### Container statuslarini ko'rish

```bash
cd /opt/rasch-bot
docker-compose ps
```

Natija shunday bo'lishi kerak:
```
NAME                 STATUS              PORTS
rasch_bot_db        running             0.0.0.0:5432->5432/tcp
rasch_telegram_bots running
```

### Loglarni ko'rish

```bash
# Barcha loglar
docker-compose logs -f

# Faqat bot loglari
docker-compose logs -f telegram_bots

# Faqat database loglari
docker-compose logs -f postgres
```

### Database tekshiruvi

```bash
# PostgreSQL'ga ulanish
docker-compose exec postgres psql -U rasch_user -d rasch_bot

# Jadvallarni ko'rish
\dt

# Chiqish
\q
```

---

## 🔄 7-BOSQICH: Avtomatik Qayta Ishga Tushirish

### Systemd service'ni yoqish

```bash
# Service'ni yoqish (reboot'dan keyin avtomatik ishga tushadi)
sudo systemctl enable rasch-bot.service

# Service'ni ishga tushirish
sudo systemctl start rasch-bot.service

# Status tekshiruvi
sudo systemctl status rasch-bot.service
```

---

## 🌐 8-BOSQICH: SSL Sertifikat (HTTPS)

Agar domeningiz bo'lsa, Let's Encrypt bilan bepul SSL sertifikat olishingiz mumkin:

### A. Domen sozlamalari

1. Domeningiz uchun A record qo'shing:
   - **Type**: A
   - **Name**: @ (yoki subdomain)
   - **Value**: Oracle VM Public IP

2. DNS propagatsiyasini kuting (5-30 daqiqa)

### B. Nginx konfiguratsiyasi

```bash
# Nginx config faylini ko'chirish
sudo cp /opt/rasch-bot/deploy/nginx.conf /etc/nginx/sites-available/rasch-bot

# YOUR_DOMAIN.com ni o'z domeningizga almashtiring
sudo sed -i 's/YOUR_DOMAIN.com/example.com/g' /etc/nginx/sites-available/rasch-bot

# Symlink yaratish
sudo ln -s /etc/nginx/sites-available/rasch-bot /etc/nginx/sites-enabled/

# Default config'ni o'chirish (agar kerak bo'lsa)
sudo rm /etc/nginx/sites-enabled/default

# Nginx'ni test qilish
sudo nginx -t

# Nginx'ni qayta ishga tushirish
sudo systemctl restart nginx
```

### C. SSL sertifikat olish

```bash
# Certbot yordamida SSL olish
sudo certbot --nginx -d example.com -d www.example.com

# Avtomatik yangilanishni yoqish
sudo systemctl enable certbot.timer
```

---

## 🛠️ Foydali Komandalar

### Container boshqaruvi

```bash
# Container'larni ishga tushirish
sudo docker-compose up -d

# Container'larni to'xtatish
sudo docker-compose down

# Container'larni qayta ishga tushirish
sudo docker-compose restart

# Loglarni ko'rish
sudo docker-compose logs -f

# Container ichiga kirish
sudo docker-compose exec telegram_bots bash
```

### Backup olish

```bash
# Database backup
sudo docker-compose exec postgres pg_dump -U rasch_user rasch_bot > /opt/rasch-bot-backups/backup_$(date +%Y%m%d_%H%M%S).sql

# To'liq loyiha backup
sudo tar -czf /opt/rasch-bot-backups/rasch-bot_$(date +%Y%m%d).tar.gz /opt/rasch-bot
```

### Backup'ni tiklash

```bash
# Database restore
sudo docker-compose exec -T postgres psql -U rasch_user rasch_bot < /path/to/backup.sql
```

### Yangilash

```bash
cd /opt/rasch-bot

# Kodni yangilash (Git orqali)
sudo git pull

# Container'larni qayta build qilish
sudo docker-compose build

# Qayta ishga tushirish
sudo docker-compose up -d
```

---

## 🐛 Muammolarni Hal Qilish

### Bot ishlamasa

```bash
# Loglarni tekshiring
docker-compose logs telegram_bots | tail -50

# Container'ni qayta ishga tushiring
docker-compose restart telegram_bots
```

### Database ulanish xatosi

```bash
# Database running ekanligini tekshiring
docker-compose ps postgres

# Database loglarini ko'ring
docker-compose logs postgres

# Connection string'ni tekshiring
docker-compose exec telegram_bots env | grep DATABASE_URL
```

### Disk to'lgan

```bash
# Disk joyini tekshirish
df -h

# Docker cache tozalash
docker system prune -a --volumes

# Eski loglarni o'chirish
sudo find /opt/rasch-bot/logs -mtime +30 -delete
```

### Port band bo'lsa

```bash
# Portni ishlatayotgan processni topish
sudo netstat -tlnp | grep 5432

# Agar kerak bo'lsa, processni to'xtatish
sudo kill -9 <PID>
```

---

## 📊 Monitoring va Logs

### Real-time monitoring

```bash
# CPU va Memory ishlatilishi
docker stats

# System resources
htop  # yoki top
```

### Log rotation sozlash

Docker Compose'da allaqachon sozlangan:
- Maksimal fayl hajmi: 10MB
- Maksimal fayllar soni: 3

---

## 🔒 Xavfsizlik Tavsiyalari

1. **Firewall**: Faqat kerakli portlarni oching
2. **Parollar**: Kuchli parollar ishlating
3. **Backuplar**: Kundalik avtomatik backup sozlang
4. **Yangilanishlar**: Tizimni muntazam yangilang
5. **SSH Keys**: Parol o'rniga SSH key ishlating
6. **Database**: Production uchun alohida database ishlating

```bash
# SSH parol autentifikatsiyasini o'chirish
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no ga o'zgartiring

sudo systemctl restart sshd
```

---

## 📞 Yordam

Agar muammo yuzaga kelsa:

1. **Loglarni tekshiring**: `docker-compose logs -f`
2. **Status tekshiruvi**: `docker-compose ps`
3. **Database tekshiruvi**: Container running ekanligiga ishonch hosil qiling
4. **Network tekshiruvi**: Portlar ochiq ekanligini tekshiring

---

## ✅ Deploy Checklist

- [ ] Oracle VM yaratildi va ishga tushdi
- [ ] SSH ulanishi ishlayapti
- [ ] Firewall sozlamalari to'g'ri
- [ ] Loyiha fayllari VM'ga yuklandi
- [ ] .env fayli to'ldirildi
- [ ] Docker va Docker Compose o'rnatildi
- [ ] deploy.sh scripti ishga tushirildi
- [ ] Container'lar running holatida
- [ ] Database migratsiyasi muvaffaqiyatli
- [ ] Loglar xatosiz
- [ ] Bot Telegram'da javob beryapti
- [ ] Backup strategiyasi sozlandi
- [ ] SSL sertifikat o'rnatildi (agar domen bor bo'lsa)

---

**Omad yor bo'lsin! 🚀**

Agar qo'shimcha savol yoki muammo bo'lsa, menga murojaat qiling.
