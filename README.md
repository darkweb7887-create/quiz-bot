# 🎯 Quiz Bot — To'liq O'rnatish Qo'llanmasi

## 📁 Loyiha Tuzilmasi

```
quiz_bot/
├── bot/
│   └── bot.py              ← Telegram bot (asosiy fayl)
├── database/
│   ├── __init__.py
│   └── db.py               ← SQLite bazasi
├── webapp/
│   └── index.html          ← Mini App (Telegram WebApp)
├── api_server.py           ← Flask API server
├── requirements.txt        ← Python kutubxonalar
├── setup.sh                ← O'rnatish skripti
├── start_all.sh            ← Ishga tushirish skripti
├── railway.toml            ← Railway deploy config
└── render.yaml             ← Render deploy config
```

---

## ⚙️ Mahalliy O'rnatish (Local)

### 1. Python o'rnatish
```bash
# Python 3.10+ kerak
python3 --version
```

### 2. Loyihani yuklab olish va o'rnatish
```bash
cd quiz_bot
chmod +x setup.sh start_all.sh
./setup.sh
```

### 3. Ishga tushirish
```bash
source venv/bin/activate
./start_all.sh
```

### 4. Mini App URL ni sozlash
`bot/bot.py` faylida bu qatorni o'zgartiring:
```python
WEBAPP_URL = "https://your-deployed-url.com"
# Masalan: WEBAPP_URL = "https://quiz-bot-api.onrender.com"
```

---

## 🌐 Deploy Qilish (Render.com — Bepul)

### Qadam 1: GitHub ga yuklash
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/SIZNING_USERNAME/quiz-bot.git
git push -u origin main
```

### Qadam 2: Render.com da sozlash

1. [render.com](https://render.com) ga kiring
2. **New → Web Service** bosing
3. GitHub repozitoriyangizni ulang
4. Quyidagilarni to'ldiring:

| Maydon | Qiymat |
|--------|--------|
| Name | `quiz-bot-api` |
| Environment | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python api_server.py` |

5. **Deploy** bosing
6. URL olasiz: `https://quiz-bot-api.onrender.com`

### Qadam 3: Bot workerani yaratish

1. **New → Background Worker** bosing
2. Bir xil repozitoriy
3. Start Command: `python bot/bot.py`
4. Deploy bosing

### Qadam 4: WEBAPP_URL ni yangilash
`bot/bot.py` faylida:
```python
WEBAPP_URL = "https://quiz-bot-api.onrender.com"
```
Keyin GitHub ga push qiling — avtomatik deploy bo'ladi.

---

## 🚂 Railway.app da Deploy (Alternativ)

1. [railway.app](https://railway.app) ga kiring
2. **New Project → GitHub Repo** tanlang
3. `railway.toml` avto-aniqlanadi
4. Environment Variables qo'shing (kerak bo'lsa)
5. Deploy!

---

## 🤖 Botning Barcha Funksiyalari

### 👤 Oddiy foydalanuvchi:
| Funksiya | Tavsif |
|----------|--------|
| `/start` | Botni boshlash, xush kelibsiz |
| `📝 Testlar` | Barcha testlarni ko'rish va yechish |
| `▶️ Testni boshlash` | Quiz o'ynash (30 soniya timer) |
| `➕ Test qo'shish` | Yangi test yaratish |
| `🏆 Reyting` | Top 10 o'yinchilar |
| `📊 Mening natijalarim` | O'z natijalari tarixi |
| `🌐 Mini App` | WebApp orqali barcha funksiyalar |

### 👑 Admin (ID: 1079953976):
| Funksiya | Tavsif |
|----------|--------|
| `/admin` | Admin panel |
| `👥 Foydalanuvchilar` | Barcha userlar ro'yxati + bloklash |
| `📋 Testlar` | Barcha testlar boshqaruvi |
| `⏳ Kutayotgan` | Tasdiqlash/rad etish |
| `📊 Statistika` | Bugun/hafta/3oy/6oy/1yil |
| `📤 Broadcast` | Barcha userlarga xabar |
| `/ban <id>` | Foydalanuvchi bloklash |
| `/unban <id>` | Blokdan chiqarish |

### 🌐 Mini App funksiyalari:
| Sahifa | Tavsif |
|--------|--------|
| 🏠 Asosiy | Statistika va tezkor kirish |
| 📝 Testlar | Test ro'yxati va yechish |
| ➕ Qo'shish | Test yaratish interfeysi |
| 🏆 Reyting | Top o'yinchilar |
| 📐 Matematika | Formula kalkulyatori |
| 🔧 Admin | Admin panel (faqat admin) |

### 📐 Matematika Kalkulyatori:
- Bayess formulasi: `P(H|A) = P(H)·P(A|H) / P(A)`
- Dispersiya: `D(X) = E(X²) - [E(X)]²`
- Kombinatsiya: `C(n,k)` va `A(n,k)`
- Matematik kutilma: `M(X) = Σxᵢ·P(xᵢ)`
- Oddiy matematik ifodalar: `sqrt(16)`, `2^10`, `sin(30)` va boshqalar

---

## 🔧 Sozlamalar (bot/bot.py)

```python
BOT_TOKEN = "7754411305:AAFUQsrXqUkWshJ1Jxc4919hchPIqKmemzk"
ADMIN_ID = 1079953976
WEBAPP_URL = "https://your-url.com"  # ← BU NI O'ZGARTIRING
```

---

## ➕ Yangi Funksiya Qo'shish

### Bot ga yangi buyruq qo'shish:
```python
# bot/bot.py ga qo'shing:

async def my_new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Yangi funksiya!")

# main() ichiga:
app.add_handler(CommandHandler("newcmd", my_new_command))
```

### API ga yangi endpoint qo'shish:
```python
# api_server.py ga qo'shing:

@app.route('/api/my-endpoint', methods=['GET'])
def my_endpoint():
    return jsonify({'data': 'hello'})
```

### Mini App ga yangi sahifa qo'shish:
```html
<!-- webapp/index.html ga qo'shing: -->

<!-- Nav tugmasi -->
<button class="nav-btn" onclick="showPage('mypage')" id="nav-mypage">
    <span class="icon">⭐</span>
    <span>Yangi</span>
</button>

<!-- Sahifa -->
<div id="page-mypage" class="page">
    <div class="card">Yangi sahifa!</div>
</div>
```

---

## 🗄️ Database Jadvallar

```sql
users          — foydalanuvchilar
tests          — testlar (approved=0/1)
questions      — savollar (options JSON)
game_sessions  — o'yinlar tarixi
user_answers   — javoblar tarixi
admins         — qo'shimcha adminlar
```

---

## ❓ Ko'p So'raladigan Savollar

**Q: Mini App ishlamayapti?**
A: `WEBAPP_URL` ni deploy qilingan URL ga o'zgartiring va botni qayta ishga tushiring.

**Q: Test ko'rinmayapti?**
A: Admin sifatida `/admin` → `⏳ Kutayotgan` bo'limiga kiring va tasdiqlang.

**Q: Bot javob bermayapti?**
A: Bot tokeni to'g'riligini tekshiring va faqat bitta bot jarayoni ishlayotganiga ishonch hosil qiling.

**Q: Yangi admin qo'shish?**
A: Database da `admins` jadvaliga `user_id` qo'shing:
```python
db.get_conn().execute("INSERT INTO admins (user_id) VALUES (?)", (USER_ID,))
```

---

## 📞 Yordam

Muammo yuzaga kelsa, bot loglarini tekshiring:
```bash
python bot/bot.py 2>&1 | tee bot.log
```
