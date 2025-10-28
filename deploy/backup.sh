#!/bin/bash

# Rasch Bot Backup Script
# Bu script database va loyiha fayllarini backup qiladi

set -e

# Konfiguratsiya
PROJECT_DIR="/opt/rasch-bot"
BACKUP_DIR="/opt/rasch-bot-backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30  # 30 kundan eski backuplarni o'chirish

# Ranglar
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rasch Bot Backup Started${NC}"
echo -e "${GREEN}========================================${NC}"

# Backup papkasini yaratish
mkdir -p $BACKUP_DIR

# 1. Database backup
echo -e "${YELLOW}[1/3] Database backup qilinmoqda...${NC}"
cd $PROJECT_DIR
docker-compose exec -T postgres pg_dump -U rasch_user rasch_bot | gzip > $BACKUP_DIR/db_backup_${DATE}.sql.gz
echo -e "${GREEN}✅ Database backup: $BACKUP_DIR/db_backup_${DATE}.sql.gz${NC}"

# 2. Data files backup
echo -e "${YELLOW}[2/3] Data files backup qilinmoqda...${NC}"
tar -czf $BACKUP_DIR/data_backup_${DATE}.tar.gz -C $PROJECT_DIR data/
echo -e "${GREEN}✅ Data backup: $BACKUP_DIR/data_backup_${DATE}.tar.gz${NC}"

# 3. Eski backuplarni o'chirish
echo -e "${YELLOW}[3/3] Eski backuplar tozalanmoqda...${NC}"
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "data_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo -e "${GREEN}✅ ${RETENTION_DAYS} kundan eski backuplar o'chirildi${NC}"

# Backup hajmini ko'rsatish
echo ""
echo -e "${GREEN}Backup yakunlandi!${NC}"
echo -e "${YELLOW}Jami backup hajmi:${NC}"
du -sh $BACKUP_DIR

echo ""
echo -e "${YELLOW}So'nggi backuplar:${NC}"
ls -lht $BACKUP_DIR | head -10
