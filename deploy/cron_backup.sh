#!/bin/bash

# Crontab uchun backup script
# Bu script cron job sifatida ishlash uchun mo'ljallangan

# Log fayl
LOG_FILE="/var/log/rasch-bot-backup.log"

# Backup scriptini ishga tushirish
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup started" >> $LOG_FILE
/opt/rasch-bot/deploy/backup.sh >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed successfully" >> $LOG_FILE
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup failed!" >> $LOG_FILE
fi
