# 🌐 Anime Telegram Botini VPS Serverga 24/7 Joylashtirish Qo'llanmasi

Botni ommaviy qilish va **kompyuteringiz o'chiq bo'lgan vaqtda ham 24/7 uzluksiz ishlashini ta'minlash** uchun uni Linux (Ubuntu) VPS serveriga joylashtirish kerak.

---

## 1-QADAM: VPS Server Olish

Har qanday arzon Ubuntu server mos keladi (Oyiga 3$ - 5$ atrofida):
- **Hetzner** (hetzner.com)
- **Vultr** (vultr.com)
- **DigitalOcean** (digitalocean.com)
- **TimeWeb** yoki **Aeza**

> **Tavsiya etiladigan OS:** Ubuntu 22.04 LTS yoki Ubuntu 24.04 LTS.

---

## 2-QADAM: Serverga Ulanish

Windows terminali (PowerShell yoki CMD) ni ochib, VPS bergan IP manzil orqali ulaning:
```bash
ssh root@SERVER_IP_MANZILINGIZ
```
*(Parol so'ralganda parolni kiriting)*

---

## 3-QADAM: Bot Fayllarini Serverga Yuklash

Fayllarni serverga yuklashning **2 ta oson usuli** bor:

### A Usul: WinSCP / FileZilla dasturi orqali (Eng osoni):
1. **WinSCP** dasturini yuklab oling va oching.
2. Server IP, `root` va parolingizni kiritib ulaning.
3. Kompyuteringizdagi `anime bot` papkasini serverdagi `/root/anime_bot` papkasiga ko'chirib tashlang.

### B Usul: Git / GitHub orqali:
```bash
git clone https://github.com/SIZNING_USERNAME/anime_bot.git /root/anime_bot
cd /root/anime_bot
```

---

## 4-QADAM: `.env` Faylini Sozlash

Serverda bot papkasiga kiring:
```bash
cd /root/anime_bot
```

`.env` fayl yaratib, bot tokeningizni yozing:
```bash
nano .env
```
Fayl ichiga yozing:
```env
BOT_TOKEN=7744383424:AAG...SIZNING_TOKENINGIZ
ADMIN_IDS=123456789
ADMIN_PASSWORD=anime2026
```
*(Saqlash uchun: `Ctrl + O`, keyin `Enter`, chiqish uchun: `Ctrl + X`)*

---

## 5-QADAM: Botni 24/7 Ishga Tushirish (Bir dona buyruq!)

Biz tayyorlab bergan `setup_vps.sh` skriptini ishga tushiring:
```bash
bash setup_vps.sh
```

Ushbu skript avtomatik ravishda:
- Python va virtual muhitni sozlaydi.
- Kutubxonalarni o'rnatadi.
- Botni Linux `systemd` servisi sifatida 24/7 avto-ishlash va server qayta yonganda ham avtomatik yoqilish rejimiga o'tkazadi.

---

## 🛠 Botni Boshqarish Buyruqlari (VPS da)

- **Bot holatini tekshirish:**
  ```bash
  sudo systemctl status animebot
  ```
- **Bot loglarini (xatoliklar va xabarlarni) jonli ko'rish:**
  ```bash
  sudo journalctl -u animebot -f
  ```
- **Botni to'xtatish:**
  ```bash
  sudo systemctl stop animebot
  ```
- **Botni qayta yoqish (Restart):**
  ```bash
  sudo systemctl restart animebot
  ```

---

🎉 **Tamom!** Endi botingiz **24 soat / 365 kun** kompyuteringiz o'chiq bo'lsa ham ommaviy ravishda barcha foydalanuvchilar uchun ishlaydi!
