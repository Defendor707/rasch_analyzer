#!/bin/bash

# Rasch Model Telegram Bot - Oracle VM uchun deployment script
# Bu skript loyihani Oracle VM'ga deploy qiladi

set -e

# Ranglar
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Konfiguratsiya
PROJECT_DIR="/opt/rasch-bot"
BACKUP_DIR="/opt/rasch-bot-backups"
DOCKER_COMPOSE_VERSION="2.20.0"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rasch Bot Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Root tekshiruvi
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Iltimos, sudo bilan ishga tushiring${NC}"
    exit 1
fi

# 1. Sistema yangilanishlarini o'rnatish
echo -e "${YELLOW}[1/10] Sistema yangilanmoqda...${NC}"
apt-get update -y
apt-get upgrade -y

# 2. Zarur paketlarni o'rnatish
echo -e "${YELLOW}[2/10] Zarur paketlar o'rnatilmoqda...${NC}"
apt-get install -y \
    git \
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    nginx \
    certbot \
    python3-certbot-nginx

# 3. Docker o'rnatish
echo -e "${YELLOW}[3/10] Docker o'rnatilmoqda...${NC}"
if ! command -v docker &> /dev/null; then
    # Docker GPG kalitini qo'shish
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Docker repository qo'shish
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Docker o'rnatish
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Docker xizmatini yoqish
    systemctl enable docker
    systemctl start docker
    
    echo -e "${GREEN}Docker muvaffaqiyatli o'rnatildi!${NC}"
else
    echo -e "${GREEN}Docker allaqachon o'rnatilgan${NC}"
fi

# 4. Docker Compose o'rnatish
echo -e "${YELLOW}[4/10] Docker Compose o'rnatilmoqda...${NC}"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    echo -e "${GREEN}Docker Compose muvaffaqiyatli o'rnatildi!${NC}"
else
    echo -e "${GREEN}Docker Compose allaqachon o'rnatilgan${NC}"
fi

# 5. Loyiha papkasini yaratish
echo -e "${YELLOW}[5/10] Loyiha papkasi tayyorlanmoqda...${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $BACKUP_DIR
mkdir -p $PROJECT_DIR/data/uploads/pdf_files
mkdir -p $PROJECT_DIR/data/results
mkdir -p $PROJECT_DIR/logs
mkdir -p $PROJECT_DIR/backups

# 6. .env faylini yaratish (agar mavjud bo'lmasa)
echo -e "${YELLOW}[6/10] Environment sozlamalari tekshirilmoqda...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  .env fayli topilmadi. Namuna yaratilmoqda...${NC}"
    cat > $PROJECT_DIR/.env << 'EOF'
# Telegram Bot Tokens
BOT_TOKEN=your_teacher_bot_token_here
STUDENT_BOT_TOKEN=your_student_bot_token_here

# PostgreSQL Database
POSTGRES_DB=rasch_bot
POSTGRES_USER=rasch_user
POSTGRES_PASSWORD=your_strong_password_here

# Agar tashqi PostgreSQL ishlatmoqchi bo'lsangiz
# DATABASE_URL=postgresql://user:password@host:port/database
EOF
    echo -e "${RED}❌ .env faylini to'ldiring va qayta ishga tushiring!${NC}"
    echo -e "${YELLOW}Joylashuv: $PROJECT_DIR/.env${NC}"
    exit 1
else
    echo -e "${GREEN}.env fayli topildi${NC}"
fi

# 7. Git repository klonlash yoki yangilash
echo -e "${YELLOW}[7/10] Loyiha kodini deploy qilish...${NC}"
if [ -d "$PROJECT_DIR/.git" ]; then
    echo -e "${YELLOW}Mavjud loyiha yangilanmoqda...${NC}"
    cd $PROJECT_DIR
    git pull
else
    echo -e "${YELLOW}Loyihani qo'lda ko'chiring yoki Git orqali klonlang${NC}"
    echo -e "${YELLOW}Masalan: git clone <repository-url> $PROJECT_DIR${NC}"
fi

# 8. Database migratsiyasini ishga tushirish
echo -e "${YELLOW}[8/10] Database sozlanmoqda...${NC}"
cd $PROJECT_DIR
docker-compose up -d postgres
sleep 10

# Database jadvallarini yaratish
docker-compose run --rm telegram_bots python setup_database.py

# 9. Docker container'larni ishga tushirish
echo -e "${YELLOW}[9/10] Bot container'lari ishga tushirilmoqda...${NC}"
docker-compose up -d

# 10. Systemd service'ni o'rnatish
echo -e "${YELLOW}[10/10] Systemd service sozlanmoqda...${NC}"
if [ -f "$PROJECT_DIR/deploy/rasch-bot.service" ]; then
    cp $PROJECT_DIR/deploy/rasch-bot.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable rasch-bot.service
    echo -e "${GREEN}Systemd service o'rnatildi${NC}"
fi

# Status tekshiruvi
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment yakunlandi!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Container statuslari:${NC}"
docker-compose ps

echo ""
echo -e "${YELLOW}Foydali komandalar:${NC}"
echo -e "  Loglarni ko'rish:        ${GREEN}docker-compose logs -f${NC}"
echo -e "  Container'ni qayta ishga tushirish: ${GREEN}docker-compose restart${NC}"
echo -e "  Container'ni to'xtatish: ${GREEN}docker-compose down${NC}"
echo -e "  Container'ni ishga tushirish:       ${GREEN}docker-compose up -d${NC}"
echo ""
echo -e "${GREEN}✅ Deployment muvaffaqiyatli yakunlandi!${NC}"
