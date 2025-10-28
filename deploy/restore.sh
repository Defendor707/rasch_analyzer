#!/bin/bash

# Rasch Bot Restore Script
# Bu script backupdan ma'lumotlarni tiklaydi

set -e

# Konfiguratsiya
PROJECT_DIR="/opt/rasch-bot"
BACKUP_DIR="/opt/rasch-bot-backups"

# Ranglar
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rasch Bot Restore Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Root tekshiruvi
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Iltimos, sudo bilan ishga tushiring${NC}"
    exit 1
fi

# Backup fayllarini ko'rsatish
echo -e "${YELLOW}Mavjud database backuplar:${NC}"
ls -lht $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null || echo "Database backup topilmadi"

echo ""
echo -e "${YELLOW}Mavjud data backuplar:${NC}"
ls -lht $BACKUP_DIR/data_backup_*.tar.gz 2>/dev/null || echo "Data backup topilmadi"

echo ""
echo -e "${RED}⚠️  OGOHLANTIRISH: Bu amal mavjud ma'lumotlarni o'chiradi!${NC}"
read -p "Davom etishni istaysizmi? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Bekor qilindi"
    exit 1
fi

# Database backup faylini so'rash
echo ""
read -p "Database backup fayl nomini kiriting (to'liq yo'l): " DB_BACKUP_FILE

if [ ! -f "$DB_BACKUP_FILE" ]; then
    echo -e "${RED}❌ Fayl topilmadi: $DB_BACKUP_FILE${NC}"
    exit 1
fi

# Data backup faylini so'rash
read -p "Data backup fayl nomini kiriting (to'liq yo'l, optional): " DATA_BACKUP_FILE

# Database restore
echo -e "${YELLOW}[1/2] Database tiklanmoqda...${NC}"
cd $PROJECT_DIR

# Database'ni tozalash
docker-compose exec -T postgres psql -U rasch_user -d postgres -c "DROP DATABASE IF EXISTS rasch_bot;"
docker-compose exec -T postgres psql -U rasch_user -d postgres -c "CREATE DATABASE rasch_bot;"

# Restore qilish
gunzip -c $DB_BACKUP_FILE | docker-compose exec -T postgres psql -U rasch_user -d rasch_bot
echo -e "${GREEN}✅ Database muvaffaqiyatli tiklandi${NC}"

# Data files restore (agar kiritilgan bo'lsa)
if [ -n "$DATA_BACKUP_FILE" ] && [ -f "$DATA_BACKUP_FILE" ]; then
    echo -e "${YELLOW}[2/2] Data files tiklanmoqda...${NC}"
    tar -xzf $DATA_BACKUP_FILE -C $PROJECT_DIR
    echo -e "${GREEN}✅ Data files muvaffaqiyatli tiklandi${NC}"
else
    echo -e "${YELLOW}[2/2] Data files restore o'tkazib yuborildi${NC}"
fi

# Container'larni qayta ishga tushirish
echo -e "${YELLOW}Container'lar qayta ishga tushirilmoqda...${NC}"
docker-compose restart

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Restore muvaffaqiyatli yakunlandi!${NC}"
echo -e "${GREEN}========================================${NC}"
