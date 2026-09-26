#!/bin/bash
# ==================================================
# Anime Telegram Bot - VPS Avtomatik O'rnatish Skripti
# OS: Ubuntu / Debian
# ==================================================

echo "=================================================="
echo "   ANIME TELEGRAM BOT - VPS SETUP (24/7 REJIM)"
echo "=================================================="

# 1. Tizimni yangilash va kerakli paketlarni o'rnatish
echo "[1/4] Tizim yangilanmoqda va kerakli paketlar o'rnatilmoqda..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git systemd

# 2. Virtual muhit yaratish va kutubxonalarni o'rnatish
echo "[2/4] Python virtual muhiti sozlanmoqda va kutubxonalar o'rnatilmoqda..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Systemd servis yaratish (24/7 avto-ishlash uchun)
echo "[3/4] Systemd avto-ishga tushirish servisi yaratilmoqda..."
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

SERVICE_FILE="/etc/systemd/system/animebot.service"

echo "[Unit]
Description=Anime Telegram Bot 24/7 Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target" | sudo tee $SERVICE_FILE > /dev/null

# 4. Servisni faollashtirish va ishga tushirish
echo "[4/4] Bot servisi ishga tushirilmoqda..."
sudo systemctl daemon-reload
sudo systemctl enable animebot
sudo systemctl restart animebot

echo ""
echo "=================================================="
echo " ✅ BOT MUVAFFAQIYATLI 24/7 ISHGA TUSHIRILDI!"
echo " 📊 Holatni ko'rish: sudo systemctl status animebot"
echo " 📋 Loglarni ko'rish: sudo journalctl -u animebot -f"
echo " ⏹ Botni to'xtatish: sudo systemctl stop animebot"
echo " 🔄 Botni qayta yoqish: sudo systemctl restart animebot"
echo "=================================================="
