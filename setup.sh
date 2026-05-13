#!/bin/bash
# Quiz Bot va API Serverni ishga tushirish

echo "🚀 Quiz Bot ishga tushirilmoqda..."
echo ""

# Virtual environment mavjudligini tekshirish
if [ ! -d "venv" ]; then
    echo "📦 Virtual environment yaratilmoqda..."
    python3 -m venv venv
fi

# Aktivlashtirish
source venv/bin/activate

# Kutubxonalarni o'rnatish
echo "📦 Kutubxonalar o'rnatilmoqda..."
pip install -r requirements.txt -q

# Database papkasini tekshirish
mkdir -p database

echo ""
echo "✅ Tayyor!"
echo ""
echo "Ishga tushirish:"
echo "  Bot: python bot/bot.py"
echo "  API: python api_server.py"
echo ""
echo "Yoki ikkalasini birga:"
echo "  ./start_all.sh"
