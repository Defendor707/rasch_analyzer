#!/bin/bash

# Cron job sozlash uchun script
# Kundalik avtomatik backup uchun

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Cron job sozlanmoqda...${NC}"

# Backup script'ga execute ruxsati berish
chmod +x /opt/rasch-bot/deploy/backup.sh
chmod +x /opt/rasch-bot/deploy/cron_backup.sh

# Cron job qo'shish (har kuni ertalab soat 3:00 da)
CRON_JOB="0 3 * * * /opt/rasch-bot/deploy/cron_backup.sh"

# Mavjud cron'ni tekshirish
if crontab -l 2>/dev/null | grep -q "cron_backup.sh"; then
    echo -e "${YELLOW}Cron job allaqachon sozlangan${NC}"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}✅ Cron job muvaffaqiyatli sozlandi (har kuni 03:00)${NC}"
fi

# Log papkasini yaratish
sudo touch /var/log/rasch-bot-backup.log
sudo chmod 644 /var/log/rasch-bot-backup.log

echo ""
echo -e "${YELLOW}Mavjud cron jobs:${NC}"
crontab -l

echo ""
echo -e "${GREEN}Cron sozlamalari yakunlandi!${NC}"
echo -e "${YELLOW}Backup har kuni ertalab soat 03:00 da avtomatik bajariladi${NC}"
echo -e "${YELLOW}Loglar: /var/log/rasch-bot-backup.log${NC}"
