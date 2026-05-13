#!/bin/bash
# Bot va API serverni parallel ishga tushirish

echo "🤖 Bot ishga tushmoqda..."
python bot/bot.py &
BOT_PID=$!

echo "🌐 API server ishga tushmoqda (port 5000)..."
python api_server.py &
API_PID=$!

echo ""
echo "✅ Ikkala jarayon ishga tushdi!"
echo "   Bot PID: $BOT_PID"
echo "   API PID: $API_PID"
echo ""
echo "To'xtatish uchun: Ctrl+C"
echo ""

# Ctrl+C bosilganda ikkalasini ham to'xtatish
trap "echo ''; echo '⛔ To\'xtatilmoqda...'; kill $BOT_PID $API_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
