# 🎬 Anime Telegram Bot (Aiogram 3 + SQLite)

Telegramdagi anime kanallari va botlari uchun maxsus tayyorlangan professional bot.

## 🚀 Imkoniyatlar

### 👤 Oddiy foydalanuvchilar uchun:
- **🔍 Kod orqali tezkor topish:** Anime kodini yozib yuborish kifoya (masalan: `1`, `105`, `naruto`). Bot bir zumda videoni yuboradi.
- **🎲 Tasodifiy anime:** Baza ichidan tasodifiy anime tavsiya qilish.
- **📋 So'nggi animelar:** Eng oxirgi yuklangan animelar ro'yxati va kodlari.
- **📤 Do'stlarga ulashish:** Har bir anime ostida do'stlarga yuborish inline tugmasi.
- **👁 Ko'rishlar hisoblagichi:** Har bir anime necha marta ko'rilgani hisoblab boriladi.

### 👑 Admin Panel uchun:
- **➕ Anime yuklash:**
  1. Video yoki hujjat (fayl) yuboriladi
  2. Nomi kiritiladi
  3. Maxsus qidiruv kodi belgilanadi (takrorlanmas bo'lishi tekshiriladi)
  4. Qisqacha tavsifi kiritiladi va tasdiqlanadi
- **📋 Animelar ro'yxati:** Sahifalab ko'rish, alohida animeni ko'rish va o'chirish.
- **🗑 Kod orqali o'chirish:** Istalgan animeni kodi orqali bazadan o'chirish.
- **📊 To'liq statistika:** Foydalanuvchilar soni, animelar soni, jami tomosha qilishlar.
- **📢 Xabar tarqatish (Broadcast):** Barcha bot foydalanuvchilariga rasm, video yoki matnli xabarni yuborish.

---

## 🔑 Adminlikni olish

Botni boshqarish uchun siz admin bo'lishingiz kerak. Buning 2 xil oson usuli bor:

1. **Telegram orqali (Eng osoni):**
   - Botga kiring va quyidagi buyruqni yuboring:
     ```
     /admin_kirish anime2026
     ```
   - Siz darhol admin bo'lasiz va sizga **👑 Admin Panel** menyusi ochiladi!
   *(Parolni `config.py` yoki `.env` orqali xohlagan vaqt o'zgartirishingiz mumkin).*

2. **`.env` fayl orqali:**
   - Botga `/id` deb yozing, u sizning Telegram ID raqamingizni chiqaradi (masalan: `123456789`).
   - `.env` faylini ochib, `ADMIN_IDS=123456789` deb yozib qo'ying.

---

## ⚙️ Ishga tushirish

1. `run.bat` faylini ikki marta bosib ishga tushiring.
   Yoki terminalda:
   ```powershell
   & "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" main.py
   ```
