#!/usr/bin/env python3
"""
Telegram Quiz Bot - To'liq funksional bot
Admin: 1079953976
"""

import logging
import asyncio
import json
import re
import math
import operator
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PollAnswerHandler
)
from database.db import Database

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7754411305:AAFUQsrXqUkWshJ1Jxc4919hchPIqKmemzk"
ADMIN_ID = 1079953976
WEBAPP_URL = "https://OneTaskQuiz.com"  # Deploy qilgandan keyin o'zgartiring

db = Database()


# ==================== HELPER FUNCTIONS ====================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID or db.is_admin(user_id)


def is_accessible(user_id: int) -> bool:
    """Foydalanuvchi botdan foydalana oladimi?"""
    if user_id == ADMIN_ID:
        return True
    if db.is_banned(user_id):
        return False
    if db.is_stopped(user_id):
        return False
    return True


def safe_math_eval(expr: str) -> str:
    """Matematik ifodani xavfsiz hisoblash"""
    allowed_names = {
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'sqrt': math.sqrt, 'log': math.log, 'log10': math.log10,
        'log2': math.log2, 'abs': abs, 'round': round,
        'pi': math.pi, 'e': math.e, 'pow': pow,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'floor': math.floor, 'ceil': math.ceil,
        'factorial': math.factorial,
        'degrees': math.degrees, 'radians': math.radians,
        'exp': math.exp,
    }

    if re.search(r'(__|\bimport\b|\bos\b|\bsys\b|\bexec\b|\beval\b|\bopen\b)', expr):
        return "❌ Ruxsat etilmagan ifoda"

    expr = expr.replace('^', '**')
    expr = expr.replace('×', '*').replace('÷', '/').replace(':', '/')

    try:
        result = eval(expr, {"__builtins__": {}}, allowed_names)
        if isinstance(result, float):
            if result == int(result):
                return str(int(result))
            return f"{result:.6g}"
        return str(result)
    except ZeroDivisionError:
        return "❌ Nolga bo'lish mumkin emas"
    except OverflowError:
        return "❌ Juda katta son"
    except Exception as e:
        return f"❌ Xato: {str(e)}"


def detect_math(text: str) -> bool:
    """Matematik ifodami?"""
    patterns = [
        r'^\s*[\d\s\+\-\*\/\^\(\)\.]+\s*[=\?]?\s*$',
        r'[\d]+\s*[\+\-\*\/\^]\s*[\d]+',
        r'\b(sin|cos|tan|sqrt|log|abs|pow|factorial)\s*\(',
        r'[\d]+\s*!',
        r'\b\d+\s*\*\*\s*\d+',
        r'^\s*[\d\+\-\*\/\^\(\)\s\.]+$',
    ]
    for p in patterns:
        if re.search(p, text.strip(), re.IGNORECASE):
            return True
    return False


# ==================== START & MAIN MENU ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.first_name or "", user.last_name or "")

    if db.is_banned(user.id) and user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz botdan bloklangansiz.")
        return

    if db.is_stopped(user.id) and user.id != ADMIN_ID:
        await update.message.reply_text("⏸ Bot siz uchun to'xtatilgan. Admin bilan bog'laning.")
        return

    webapp_btn = KeyboardButton(
        text="🌐 Mini App ochish",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )

    keyboard = ReplyKeyboardMarkup(
        [[webapp_btn],
         ["📝 Testlar", "🏆 Reyting"],
         ["➕ Test qo'shish", "📊 Mening natijalarim"],
         ["🧮 Kalkulyator"]],
        resize_keyboard=True
    )

    welcome_text = (
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        "🎯 <b>Quiz Botga xush kelibsiz!</b>\n\n"
        "Bu bot orqali siz:\n"
        "📝 Testlar yechishingiz\n"
        "➕ O'z testlaringizni qo'shishingiz\n"
        "🏆 Reytingda ko'rishingiz\n"
        "🧮 Matematik hisob-kitob qilishingiz mumkin!\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )

    await update.message.reply_html(welcome_text, reply_markup=keyboard)

    if is_admin(user.id):
        admin_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")]
        ])
        await update.message.reply_text("🔑 Admin sifatida kirdingiz!", reply_markup=admin_keyboard)


# ==================== TEST LIST ====================

async def show_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_accessible(user.id):
        await update.message.reply_text("❌ Siz botdan foydalana olmaysiz.")
        return

    tests = db.get_tests(approved_only=True)

    if not tests:
        await update.message.reply_text("📭 Hozircha testlar yo'q. Birinchi bo'lib test qo'shing!")
        return

    keyboard = []
    for test in tests:
        q_count = db.get_question_count(test['id'])
        btn_text = f"📋 {test['title']} ({q_count} ta savol)"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"test_info_{test['id']}")])

    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])

    await update.message.reply_text(
        "📝 <b>Mavjud testlar:</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== TEST INFO ====================

async def test_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    test_id = int(query.data.split("_")[-1])
    test = db.get_test(test_id)

    if not test:
        await query.edit_message_text("❌ Test topilmadi.")
        return

    q_count = db.get_question_count(test_id)
    attempts = db.get_test_attempts(test_id)
    creator = db.get_user(test['creator_id'])
    creator_name = creator['first_name'] if creator else "Noma'lum"

    text = (
        f"📋 <b>{test['title']}</b>\n\n"
        f"📝 Savollar soni: {q_count}\n"
        f"👤 Muallif: {creator_name}\n"
        f"📊 Urinishlar: {attempts}\n"
        f"📅 Qo'shilgan: {test['created_at'][:10]}\n"
    )

    if test.get('description'):
        text += f"\n📖 {test['description']}\n"

    keyboard = [
        [InlineKeyboardButton("▶️ Testni boshlash", callback_data=f"start_test_{test_id}")],
        [InlineKeyboardButton("🔙 Testlar ro'yxati", callback_data="test_list")]
    ]

    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== QUIZ PLAY ====================

async def start_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if not is_accessible(user.id):
        await query.answer("❌ Siz botdan foydalana olmaysiz!", show_alert=True)
        return

    test_id = int(query.data.split("_")[-1])
    questions = db.get_questions(test_id)

    if not questions:
        await query.edit_message_text("❌ Bu testda savollar yo'q.")
        return

    session_id = db.start_session(user.id, test_id)
    session = {
        'session_id': session_id,
        'test_id': test_id,
        'questions': questions,
        'current': 0,
        'correct': 0,
        'answers': [],
        'chat_id': query.message.chat_id
    }
    context.user_data['session'] = session
    context.bot_data[f"session_{user.id}"] = session

    await query.edit_message_text(
        f"🎯 Test boshlanmoqda! {len(questions)} ta savol.\n\nDiqqat bilan o'qing va javob bering!"
    )
    await send_question(query.message.chat_id, context, user.id)


async def send_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = context.user_data.get('session') or context.bot_data.get(f"session_{user_id}")
    if not session:
        return

    idx = session['current']
    questions = session['questions']

    if idx >= len(questions):
        await finish_quiz(chat_id, context, user_id)
        return

    q = questions[idx]
    options = q['options'] if isinstance(q['options'], list) else json.loads(q['options'])

    progress = f"[{idx + 1}/{len(questions)}]"

    try:
        poll_msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"{progress} {q['question'][:255]}",
            options=[str(o)[:100] for o in options[:10]],
            type='quiz',
            correct_option_id=q['correct_answer'],
            explanation=(q.get('explanation') or '')[:200],
            is_anonymous=False,
            open_period=30
        )
        session['current_poll_id'] = poll_msg.poll.id
        session['current_msg_id'] = poll_msg.message_id
        session['chat_id'] = chat_id
        context.user_data['session'] = session
        context.bot_data[f"session_{user_id}"] = session
    except Exception as e:
        logger.error(f"Poll send error: {e}")
        await send_question_inline(chat_id, context, user_id)


async def send_question_inline(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = context.user_data.get('session') or context.bot_data.get(f"session_{user_id}")
    if not session:
        return

    idx = session['current']
    questions = session['questions']
    q = questions[idx]
    options = q['options'] if isinstance(q['options'], list) else json.loads(q['options'])

    progress = f"❓ Savol {idx + 1}/{len(questions)}"

    keyboard = []
    for i, opt in enumerate(options):
        keyboard.append([InlineKeyboardButton(f"{chr(65 + i)}) {opt}", callback_data=f"answer_{i}_{q['id']}")])

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{progress}\n\n<b>{q['question']}</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    session = context.user_data.get('session')
    if not session:
        await query.answer("Session tugagan!")
        return

    parts = query.data.split("_")
    chosen = int(parts[1])
    q_id = int(parts[2])

    idx = session['current']
    questions = session['questions']

    if idx >= len(questions):
        await query.answer("Test tugagan!")
        return

    q = questions[idx]
    is_correct = chosen == q['correct_answer']

    if is_correct:
        session['correct'] += 1
        result_text = "✅ To'g'ri!"
    else:
        options = q['options'] if isinstance(q['options'], list) else json.loads(q['options'])
        correct_opt = options[q['correct_answer']]
        result_text = f"❌ Noto'g'ri! To'g'ri javob: {correct_opt}"

    session['answers'].append({'q_id': q_id, 'chosen': chosen, 'correct': is_correct})
    session['current'] += 1
    context.user_data['session'] = session
    context.bot_data[f"session_{user.id}"] = session

    await query.answer(result_text, show_alert=True)
    try:
        await query.edit_message_reply_markup(None)
    except Exception:
        pass

    if q.get('explanation'):
        await query.message.reply_text(f"💡 {q['explanation']}")

    await asyncio.sleep(0.5)
    await send_question(query.message.chat_id, context, user.id)


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Native poll javoblarini qayta ishlash"""
    poll_answer = update.poll_answer
    user_id = poll_answer.user.id

    session_key = f"session_{user_id}"
    session = context.bot_data.get(session_key)

    if not session:
        return

    if poll_answer.option_ids:
        chosen = poll_answer.option_ids[0]
        idx = session['current']
        questions = session['questions']

        if idx < len(questions):
            q = questions[idx]
            is_correct = chosen == q['correct_answer']

            if is_correct:
                session['correct'] += 1

            session['answers'].append({'q_id': q['id'], 'chosen': chosen, 'correct': is_correct})
            session['current'] += 1
            context.bot_data[session_key] = session

            await asyncio.sleep(1.5)
            chat_id = session.get('chat_id')
            if chat_id:
                await send_question(chat_id, context, user_id)


async def finish_quiz(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = context.user_data.get('session') or context.bot_data.get(f"session_{user_id}")
    if not session:
        return

    total = len(session['questions'])
    correct = session['correct']
    wrong = total - correct
    percentage = (correct / total * 100) if total > 0 else 0

    db.save_result(session['session_id'], user_id, session['test_id'], correct, total)

    if percentage >= 90:
        grade = "🏆 A'lo!"
        emoji = "🌟"
    elif percentage >= 75:
        grade = "👍 Yaxshi!"
        emoji = "✨"
    elif percentage >= 60:
        grade = "😊 Qoniqarli"
        emoji = "👌"
    else:
        grade = "📚 Ko'proq o'qing"
        emoji = "💪"

    text = (
        f"{emoji} <b>Test yakunlandi!</b>\n\n"
        f"✅ To'g'ri: {correct}\n"
        f"❌ Noto'g'ri: {wrong}\n"
        f"📊 Foiz: {percentage:.1f}%\n"
        f"🎯 Baho: {grade}\n"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Qayta o'ynash", callback_data=f"start_test_{session['test_id']}")],
        [InlineKeyboardButton("📝 Boshqa testlar", callback_data="test_list")],
        [InlineKeyboardButton("🏆 Reyting", callback_data="show_rating")]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data.pop('session', None)
    context.bot_data.pop(f"session_{user_id}", None)


# ==================== CALCULATOR ====================

async def show_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_accessible(user.id):
        return

    text = (
        "🧮 <b>Kalkulyator</b>\n\n"
        "Matematik ifodani yuboring:\n\n"
        "Misol:\n"
        "• <code>2 + 2</code>\n"
        "• <code>sqrt(16)</code>\n"
        "• <code>sin(pi/2)</code>\n"
        "• <code>2^10</code>\n"
        "• <code>factorial(5)</code>\n"
        "• <code>log(100, 10)</code>\n\n"
        "Yoki tugmachalar orqali hisoblang:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("7", callback_data="calc_7"),
         InlineKeyboardButton("8", callback_data="calc_8"),
         InlineKeyboardButton("9", callback_data="calc_9"),
         InlineKeyboardButton("÷", callback_data="calc_/")],
        [InlineKeyboardButton("4", callback_data="calc_4"),
         InlineKeyboardButton("5", callback_data="calc_5"),
         InlineKeyboardButton("6", callback_data="calc_6"),
         InlineKeyboardButton("×", callback_data="calc_*")],
        [InlineKeyboardButton("1", callback_data="calc_1"),
         InlineKeyboardButton("2", callback_data="calc_2"),
         InlineKeyboardButton("3", callback_data="calc_3"),
         InlineKeyboardButton("-", callback_data="calc_-")],
        [InlineKeyboardButton("0", callback_data="calc_0"),
         InlineKeyboardButton(".", callback_data="calc_."),
         InlineKeyboardButton("=", callback_data="calc_="),
         InlineKeyboardButton("+", callback_data="calc_+")],
        [InlineKeyboardButton("( )", callback_data="calc_("),
         InlineKeyboardButton("^", callback_data="calc_^"),
         InlineKeyboardButton("⌫", callback_data="calc_back"),
         InlineKeyboardButton("🗑️ Tozalash", callback_data="calc_clear")],
    ])

    context.user_data['calc_expr'] = ''
    await update.message.reply_html(text, reply_markup=keyboard)


async def handle_calculator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data.replace("calc_", "")
    expr = context.user_data.get('calc_expr', '')

    if action == 'clear':
        expr = ''
    elif action == 'back':
        expr = expr[:-1]
    elif action == '(':
        if expr and expr[-1].isdigit():
            expr += '*('
        else:
            expr += '('
    elif action == '=':
        if expr:
            result = safe_math_eval(expr)
            await query.edit_message_text(
                f"🧮 <b>Kalkulyator</b>\n\n"
                f"📥 Ifoda: <code>{expr}</code>\n"
                f"📤 Natija: <b>{result}</b>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Yana hisoblash", callback_data="calc_reset")]
                ])
            )
            context.user_data['calc_expr'] = ''
            return
        else:
            await query.answer("Ifoda kiritilmagan!", show_alert=True)
            return
    elif action == 'reset':
        context.user_data['calc_expr'] = ''
        await query.edit_message_text(
            "🧮 <b>Kalkulyator</b>\n\nIfoda: <code> </code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("7", callback_data="calc_7"),
                 InlineKeyboardButton("8", callback_data="calc_8"),
                 InlineKeyboardButton("9", callback_data="calc_9"),
                 InlineKeyboardButton("÷", callback_data="calc_/")],
                [InlineKeyboardButton("4", callback_data="calc_4"),
                 InlineKeyboardButton("5", callback_data="calc_5"),
                 InlineKeyboardButton("6", callback_data="calc_6"),
                 InlineKeyboardButton("×", callback_data="calc_*")],
                [InlineKeyboardButton("1", callback_data="calc_1"),
                 InlineKeyboardButton("2", callback_data="calc_2"),
                 InlineKeyboardButton("3", callback_data="calc_3"),
                 InlineKeyboardButton("-", callback_data="calc_-")],
                [InlineKeyboardButton("0", callback_data="calc_0"),
                 InlineKeyboardButton(".", callback_data="calc_."),
                 InlineKeyboardButton("=", callback_data="calc_="),
                 InlineKeyboardButton("+", callback_data="calc_+")],
                [InlineKeyboardButton("( )", callback_data="calc_("),
                 InlineKeyboardButton("^", callback_data="calc_^"),
                 InlineKeyboardButton("⌫", callback_data="calc_back"),
                 InlineKeyboardButton("🗑️ Tozalash", callback_data="calc_clear")],
            ])
        )
        return
    else:
        expr += action

    context.user_data['calc_expr'] = expr
    display = expr if expr else ' '

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("7", callback_data="calc_7"),
         InlineKeyboardButton("8", callback_data="calc_8"),
         InlineKeyboardButton("9", callback_data="calc_9"),
         InlineKeyboardButton("÷", callback_data="calc_/")],
        [InlineKeyboardButton("4", callback_data="calc_4"),
         InlineKeyboardButton("5", callback_data="calc_5"),
         InlineKeyboardButton("6", callback_data="calc_6"),
         InlineKeyboardButton("×", callback_data="calc_*")],
        [InlineKeyboardButton("1", callback_data="calc_1"),
         InlineKeyboardButton("2", callback_data="calc_2"),
         InlineKeyboardButton("3", callback_data="calc_3"),
         InlineKeyboardButton("-", callback_data="calc_-")],
        [InlineKeyboardButton("0", callback_data="calc_0"),
         InlineKeyboardButton(".", callback_data="calc_."),
         InlineKeyboardButton("=", callback_data="calc_="),
         InlineKeyboardButton("+", callback_data="calc_+")],
        [InlineKeyboardButton("( )", callback_data="calc_("),
         InlineKeyboardButton("^", callback_data="calc_^"),
         InlineKeyboardButton("⌫", callback_data="calc_back"),
         InlineKeyboardButton("🗑️ Tozalash", callback_data="calc_clear")],
    ])

    try:
        await query.edit_message_text(
            f"🧮 <b>Kalkulyator</b>\n\nIfoda: <code>{display}</code>",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except Exception:
        pass


# ==================== ADD TEST ====================

async def add_test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_accessible(user.id):
        await update.message.reply_text("❌ Siz botdan foydalana olmaysiz.")
        return

    context.user_data['adding_test'] = {'step': 'title'}

    await update.message.reply_text(
        "➕ <b>Yangi test qo'shish</b>\n\n"
        "1️⃣ Avval test nomini kiriting:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]])
    )


async def handle_test_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    adding = context.user_data.get('adding_test')
    if not adding:
        return

    step = adding.get('step')

    if step == 'title':
        adding['title'] = text
        adding['step'] = 'description'
        context.user_data['adding_test'] = adding

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ O'tkazib yuborish", callback_data="skip_description")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]
        ])
        await update.message.reply_text(
            f"✅ Test nomi: <b>{text}</b>\n\n2️⃣ Test tavsifini kiriting (ixtiyoriy):",
            parse_mode='HTML',
            reply_markup=keyboard
        )

    elif step == 'description':
        adding['description'] = text
        adding['step'] = 'question'
        adding['questions'] = []
        adding['current_q'] = {}
        context.user_data['adding_test'] = adding

        await update.message.reply_text(
            f"✅ Tavsif saqlandi!\n\n"
            "3️⃣ Endi savollarni kiriting.\n"
            "📝 <b>1-savol matnini yozing:</b>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]])
        )

    elif step == 'question':
        adding['current_q'] = {'question': text, 'options': []}
        adding['step'] = 'options'
        adding['option_count'] = 0
        context.user_data['adding_test'] = adding

        await update.message.reply_text(
            f"❓ Savol: <b>{text}</b>\n\n"
            "📌 Endi javob variantlarini kiriting.\n"
            "✏️ <b>A) varianti:</b>",
            parse_mode='HTML'
        )

    elif step == 'options':
        count = adding.get('option_count', 0)
        adding['current_q']['options'].append(text)
        count += 1
        adding['option_count'] = count
        context.user_data['adding_test'] = adding

        if count < 2:
            letters = ['A', 'B', 'C', 'D', 'E']
            await update.message.reply_text(
                f"✅ {chr(64 + count)}) {text}\n\n✏️ <b>{letters[count]}) varianti:</b>",
                parse_mode='HTML'
            )
        elif count < 5:
            letters = ['A', 'B', 'C', 'D', 'E']
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Variantlar yetarli", callback_data="options_done")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]
            ])
            await update.message.reply_text(
                f"✅ {chr(64 + count)}) {text}\n\n"
                f"✏️ <b>{letters[count]}) varianti</b> yoki 'Variantlar yetarli' tugmasini bosing:",
                parse_mode='HTML',
                reply_markup=keyboard
            )
        else:
            adding['step'] = 'correct'
            context.user_data['adding_test'] = adding
            await ask_correct_answer(update, context)

    elif step == 'correct':
        try:
            correct_idx = int(text) - 1
            options = adding['current_q']['options']
            if 0 <= correct_idx < len(options):
                adding['current_q']['correct_answer'] = correct_idx
                adding['step'] = 'explanation'
                context.user_data['adding_test'] = adding

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭️ O'tkazib yuborish", callback_data="skip_explanation")],
                    [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]
                ])
                await update.message.reply_text(
                    f"✅ To'g'ri javob: <b>{correct_idx + 1}) {options[correct_idx]}</b>\n\n"
                    "💡 Izoh kiriting (ixtiyoriy):",
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(f"❌ 1 dan {len(options)} gacha raqam kiriting!")
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam kiriting!")

    elif step == 'explanation':
        adding['current_q']['explanation'] = text
        adding['questions'].append(adding['current_q'].copy())
        adding['current_q'] = {}
        adding['step'] = 'next_question'
        context.user_data['adding_test'] = adding

        q_num = len(adding['questions'])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yana savol qo'shish", callback_data="add_more_q")],
            [InlineKeyboardButton("✅ Testni saqlash", callback_data="save_test")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]
        ])
        await update.message.reply_text(
            f"✅ {q_num}-savol saqlandi!\n\nNima qilmoqchisiz?",
            reply_markup=keyboard
        )


async def ask_correct_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adding = context.user_data.get('adding_test')
    options = adding['current_q']['options']

    text = "🎯 <b>To'g'ri javob raqamini kiriting:</b>\n\n"
    for i, opt in enumerate(options):
        text += f"{i + 1}) {opt}\n"

    await update.message.reply_text(text, parse_mode='HTML')


async def options_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    adding = context.user_data.get('adding_test')
    if not adding:
        return

    if len(adding['current_q'].get('options', [])) < 2:
        await query.answer("Kamida 2 ta variant kerak!", show_alert=True)
        return

    adding['step'] = 'correct'
    context.user_data['adding_test'] = adding

    options = adding['current_q']['options']
    text = "🎯 <b>To'g'ri javob raqamini kiriting:</b>\n\n"
    for i, opt in enumerate(options):
        text += f"{i + 1}) {opt}\n"

    await query.edit_message_text(text, parse_mode='HTML')


async def skip_explanation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    adding = context.user_data.get('adding_test')
    if not adding:
        return

    adding['current_q']['explanation'] = ''
    adding['questions'].append(adding['current_q'].copy())
    adding['current_q'] = {}
    adding['step'] = 'next_question'
    context.user_data['adding_test'] = adding

    q_num = len(adding['questions'])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yana savol qo'shish", callback_data="add_more_q")],
        [InlineKeyboardButton("✅ Testni saqlash", callback_data="save_test")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]
    ])
    await query.edit_message_text(
        f"✅ {q_num}-savol saqlandi!\n\nNima qilmoqchisiz?",
        reply_markup=keyboard
    )


async def skip_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    adding = context.user_data.get('adding_test')
    if not adding:
        return

    adding['description'] = ''
    adding['step'] = 'question'
    adding['questions'] = []
    adding['current_q'] = {}
    context.user_data['adding_test'] = adding

    await query.edit_message_text(
        "3️⃣ Endi savollarni kiriting.\n📝 <b>1-savol matnini yozing:</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]])
    )


async def add_more_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    adding = context.user_data.get('adding_test')
    if not adding:
        return

    adding['step'] = 'question'
    adding['current_q'] = {}
    context.user_data['adding_test'] = adding

    q_num = len(adding['questions']) + 1
    await query.edit_message_text(
        f"📝 <b>{q_num}-savol matnini yozing:</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]])
    )


async def save_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    adding = context.user_data.get('adding_test')
    if not adding:
        return

    user = query.from_user
    questions = adding.get('questions', [])

    if not questions:
        await query.edit_message_text("❌ Kamida bitta savol kerak!")
        return

    approved = is_admin(user.id)
    test_id = db.save_test(
        creator_id=user.id,
        title=adding['title'],
        description=adding.get('description', ''),
        questions=questions,
        approved=approved
    )

    context.user_data.pop('adding_test', None)

    if approved:
        await query.edit_message_text(
            f"✅ <b>Test muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📋 Nomi: {adding['title']}\n"
            f"❓ Savollar: {len(questions)} ta",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            f"⏳ <b>Test admin tekshiruviga yuborildi!</b>\n\n"
            f"📋 Nomi: {adding['title']}\n"
            f"❓ Savollar: {len(questions)} ta\n\n"
            "Admin tasdiqlashidan keyin ko'rinadi.",
            parse_mode='HTML'
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"📬 Yangi test tasdiqlash kutmoqda!\n\n"
                    f"👤 Muallif: {user.first_name} (@{user.username or 'N/A'})\n"
                    f"📋 Nomi: {adding['title']}\n"
                    f"❓ Savollar: {len(questions)} ta"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_test_{test_id}"),
                     InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_test_{test_id}")]
                ])
            )
        except Exception as e:
            logger.error(f"Admin notify error: {e}")


async def cancel_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop('adding_test', None)
    await query.edit_message_text("❌ Bekor qilindi.")


# ==================== RATING ====================

async def show_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = db.get_top_users(10)

    if not top_users:
        text = "🏆 <b>Reyting bo'sh</b>\n\nHali hech kim test yechimagan."
    else:
        text = "🏆 <b>Top 10 o'yinchi:</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]

        for i, u in enumerate(top_users):
            medal = medals[i] if i < 3 else f"{i + 1}."
            name = u['first_name'] or "Anonim"
            text += f"{medal} {name}: {u['total_correct']}/{u['total_questions']} ({u['percentage']:.0f}%)\n"

    if hasattr(update, 'message') and update.message:
        await update.message.reply_html(text)
    else:
        query = update.callback_query
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]]
            )
        )


# ==================== MY RESULTS ====================

async def my_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    results = db.get_user_results(user.id)

    if not results:
        await update.message.reply_text("📊 Siz hali hech qanday test yechmagansiz.")
        return

    text = f"📊 <b>Sizning natijalaringiz ({user.first_name}):</b>\n\n"

    for r in results[:10]:
        percentage = (r['correct'] / r['total'] * 100) if r['total'] > 0 else 0
        text += (
            f"📋 {r['test_title']}\n"
            f"   ✅ {r['correct']}/{r['total']} ({percentage:.0f}%)\n"
            f"   📅 {str(r['taken_at'])[:10]}\n\n"
        )

    await update.message.reply_html(text)


# ==================== MATH MESSAGE HANDLER ====================

async def handle_math_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matematik ifodalarni to'g'ridan-to'g'ri hisoblash"""
    text = update.message.text.strip()

    if detect_math(text):
        expr = text.replace('=', '').replace('?', '').strip()
        result = safe_math_eval(expr)
        await update.message.reply_text(
            f"🧮 <code>{expr}</code> = <b>{result}</b>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❓ Tushunmadim. Quyidagilardan birini tanlang:\n\n"
            "📝 Testlar — testlar ro'yxatini ko'rish\n"
            "🧮 Kalkulyator — matematik hisob-kitob\n"
            "➕ Test qo'shish — yangi test yaratish"
        )


# ==================== ADMIN PANEL ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text("❌ Ruxsat yo'q!")
        return

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.answer()

    stats = db.get_stats()

    text = (
        "🔧 <b>Admin Panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"📋 Jami testlar: {stats['total_tests']}\n"
        f"🎮 Jami o'yinlar: {stats['total_games']}\n"
        f"⏳ Tasdiqlash kutayotgan: {stats['pending_tests']}\n"
        f"🚫 Bloklangan: {stats['banned_users']}\n"
        f"⏸ To'xtatilgan: {stats['stopped_users']}\n"
    )

    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users"),
         InlineKeyboardButton("📋 Testlar", callback_data="admin_tests")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
         InlineKeyboardButton("⏳ Kutayotgan", callback_data="admin_pending")],
        [InlineKeyboardButton("📤 Xabar yuborish", callback_data="admin_broadcast"),
         InlineKeyboardButton("🚫 Bloklash", callback_data="admin_ban")],
        [InlineKeyboardButton("🔍 ID bo'yicha qidirish", callback_data="admin_search")],
    ]

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if not is_admin(user.id):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "admin_panel":
        await admin_panel(update, context)

    elif action == "admin_users":
        await show_admin_users(update, context)

    elif action == "admin_tests":
        await show_admin_tests(update, context)

    elif action == "admin_stats":
        await show_admin_stats(update, context)

    elif action == "admin_pending":
        await show_pending_tests(update, context)

    elif action == "admin_broadcast":
        context.user_data['admin_action'] = 'broadcast'
        await query.edit_message_text(
            "📤 <b>Barcha foydalanuvchilarga xabar:</b>\n\nXabar matnini kiriting:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif action == "admin_ban":
        context.user_data['admin_action'] = 'ban_by_id'
        await query.edit_message_text(
            "🚫 Bloklash uchun foydalanuvchi ID sini kiriting:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif action == "admin_search":
        context.user_data['admin_action'] = 'search_user'
        await query.edit_message_text(
            "🔍 Foydalanuvchi ID sini kiriting:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif action == "admin_custom_date":
        context.user_data['admin_action'] = 'custom_date'
        await query.edit_message_text(
            "📅 Sana oralig'ini kiriting (format: YYYY-MM-DD YYYY-MM-DD):\n\nMisol: 2024-01-01 2024-12-31",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_stats")]])
        )

    elif action.startswith("approve_test_"):
        test_id = int(action.split("_")[-1])
        db.approve_test(test_id)
        test = db.get_test(test_id)
        await query.edit_message_text(
            f"✅ Test tasdiqlandi!\n\n📋 Nomi: {test['title'] if test else test_id}"
        )

    elif action.startswith("reject_test_"):
        test_id = int(action.split("_")[-1])
        db.reject_test(test_id)
        await query.edit_message_text("❌ Test rad etildi va o'chirildi!")

    elif action.startswith("ban_user_"):
        uid = int(action.split("_")[-1])
        db.ban_user(uid)
        u = db.get_user(uid)
        name = u['first_name'] if u else uid
        await query.edit_message_text(
            f"🚫 {name} ({uid}) bloklandi!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Blokdan chiqarish", callback_data=f"unban_user_{uid}")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
            ])
        )

    elif action.startswith("unban_user_"):
        uid = int(action.split("_")[-1])
        db.unban_user(uid)
        u = db.get_user(uid)
        name = u['first_name'] if u else uid
        await query.edit_message_text(
            f"✅ {name} ({uid}) blokdan chiqarildi!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 Qayta bloklash", callback_data=f"ban_user_{uid}")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
            ])
        )

    elif action.startswith("stop_user_"):
        uid = int(action.split("_")[-1])
        db.stop_user(uid)
        u = db.get_user(uid)
        name = u['first_name'] if u else uid
        await query.edit_message_text(
            f"⏸ {name} ({uid}) uchun bot to'xtatildi!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Botni yoqish", callback_data=f"unstop_user_{uid}")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
            ])
        )

    elif action.startswith("unstop_user_"):
        uid = int(action.split("_")[-1])
        db.unstop_user(uid)
        u = db.get_user(uid)
        name = u['first_name'] if u else uid
        await query.edit_message_text(
            f"▶️ {name} ({uid}) uchun bot yoqildi!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏸ To'xtatish", callback_data=f"stop_user_{uid}")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
            ])
        )

    elif action.startswith("delete_test_"):
        test_id = int(action.split("_")[-1])
        test = db.get_test(test_id)
        name = test['title'] if test else test_id
        await query.edit_message_text(
            f"⚠️ <b>{name}</b> testini o'chirmoqchimisiz?",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"confirm_delete_test_{test_id}"),
                 InlineKeyboardButton("❌ Yo'q", callback_data="admin_tests")]
            ])
        )

    elif action.startswith("confirm_delete_test_"):
        test_id = int(action.split("_")[-1])
        db.delete_test(test_id)
        await query.edit_message_text(
            "🗑️ Test o'chirildi!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Testlar", callback_data="admin_tests")]])
        )

    elif action == "test_list":
        await show_tests_message(query.message, context)

    elif action.startswith("test_info_"):
        await test_info_callback(update, context)

    elif action.startswith("start_test_"):
        await start_test_callback(update, context)

    elif action.startswith("answer_"):
        await handle_answer(update, context)

    elif action == "show_rating":
        await show_rating(update, context)

    elif action == "main_menu":
        stats_text = "📋 Asosiy menyu"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Testlar", callback_data="test_list"),
             InlineKeyboardButton("🏆 Reyting", callback_data="show_rating")]
        ])
        await query.edit_message_text(stats_text, reply_markup=keyboard)

    elif action.startswith("calc_"):
        await handle_calculator_callback(update, context)


async def show_tests_message(message, context):
    tests = db.get_tests(approved_only=True)
    if not tests:
        await message.reply_text("📭 Hozircha testlar yo'q.")
        return

    keyboard = []
    for test in tests:
        q_count = db.get_question_count(test['id'])
        keyboard.append([InlineKeyboardButton(
            f"📋 {test['title']} ({q_count}❓)",
            callback_data=f"test_info_{test['id']}"
        )])

    await message.reply_text(
        "📝 <b>Mavjud testlar:</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("📅 Bugun", callback_data="admin_users_today"),
         InlineKeyboardButton("📅 1 hafta", callback_data="admin_users_week")],
        [InlineKeyboardButton("📅 3 oy", callback_data="admin_users_3months"),
         InlineKeyboardButton("📅 6 oy", callback_data="admin_users_6months")],
        [InlineKeyboardButton("📅 1 yil", callback_data="admin_users_year"),
         InlineKeyboardButton("📅 Barchasi", callback_data="admin_users_all")],
        [InlineKeyboardButton("📅 Maxsus sana", callback_data="admin_users_custom")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]

    await query.edit_message_text(
        "👥 <b>Foydalanuvchilar</b>\n\nQaysi davr uchun ko'rmoqchisiz?",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tests = db.get_all_tests()

    if not tests:
        await query.edit_message_text(
            "📋 Testlar yo'q.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]])
        )
        return

    text = "📋 <b>Barcha testlar:</b>\n\n"
    keyboard = []

    for t in tests:
        status = "✅" if t.get('approved') else "⏳"
        q_count = db.get_question_count(t['id'])
        creator = db.get_user(t['creator_id'])
        creator_name = creator['first_name'] if creator else "Noma'lum"
        text += f"{status} <b>{t['title']}</b>\n"
        text += f"   👤 {creator_name} | ❓ {q_count} ta | 📅 {str(t['created_at'])[:10]}\n\n"

        row = []
        if not t.get('approved'):
            row.append(InlineKeyboardButton("✅", callback_data=f"approve_test_{t['id']}"))
        row.append(InlineKeyboardButton(f"🗑️ {t['title'][:15]}", callback_data=f"delete_test_{t['id']}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])

    if len(text) > 3500:
        text = text[:3500] + "\n\n..."

    await query.edit_message_text(
        text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_pending_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tests = db.get_pending_tests()

    if not tests:
        await query.edit_message_text(
            "✅ Tasdiqlash kutayotgan testlar yo'q!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )
        return

    text = "⏳ <b>Tasdiqlash kutayotgan testlar:</b>\n\n"
    keyboard = []

    for t in tests:
        creator = db.get_user(t['creator_id'])
        creator_name = creator['first_name'] if creator else "Noma'lum"
        username = f"@{creator['username']}" if creator and creator.get('username') else ""
        q_count = db.get_question_count(t['id'])

        text += f"📋 <b>{t['title']}</b>\n"
        text += f"   👤 {creator_name} {username} | ❓ {q_count} ta\n"
        text += f"   📅 {str(t['created_at'])[:10]}\n\n"

        keyboard.append([
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_test_{t['id']}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_test_{t['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])

    await query.edit_message_text(
        text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    stats_today = db.get_stats_by_period('today')
    stats_week = db.get_stats_by_period('week')
    stats_month = db.get_stats_by_period('month')
    stats_3month = db.get_stats_by_period('3months')
    stats_6month = db.get_stats_by_period('6months')
    stats_year = db.get_stats_by_period('year')
    stats_all = db.get_stats()

    text = (
        "📊 <b>Statistika:</b>\n\n"
        f"📅 <b>Bugun:</b>\n"
        f"   👥 Yangi: {stats_today['new_users']} | 🎮: {stats_today['games']} | 📋: {stats_today['new_tests']}\n\n"
        f"📅 <b>1 hafta:</b>\n"
        f"   👥 Yangi: {stats_week['new_users']} | 🎮: {stats_week['games']} | 📋: {stats_week['new_tests']}\n\n"
        f"📅 <b>1 oy:</b>\n"
        f"   👥 Yangi: {stats_month['new_users']} | 🎮: {stats_month['games']} | 📋: {stats_month['new_tests']}\n\n"
        f"📅 <b>3 oy:</b>\n"
        f"   👥 Yangi: {stats_3month['new_users']} | 🎮: {stats_3month['games']} | 📋: {stats_3month['new_tests']}\n\n"
        f"📅 <b>6 oy:</b>\n"
        f"   👥 Yangi: {stats_6month['new_users']} | 🎮: {stats_6month['games']} | 📋: {stats_6month['new_tests']}\n\n"
        f"📅 <b>1 yil:</b>\n"
        f"   👥 Yangi: {stats_year['new_users']} | 🎮: {stats_year['games']} | 📋: {stats_year['new_tests']}\n\n"
        f"📊 <b>Jami:</b>\n"
        f"   👥 {stats_all['total_users']} ta foydalanuvchi\n"
        f"   📋 {stats_all['total_tests']} ta test\n"
        f"   🎮 {stats_all['total_games']} ta o'yin\n"
        f"   🚫 {stats_all['banned_users']} ta bloklangan\n"
    )

    keyboard = [
        [InlineKeyboardButton("📅 Maxsus sana oralig'i", callback_data="admin_custom_date")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]

    await query.edit_message_text(
        text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== ADMIN MESSAGE HANDLER ====================

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        return

    admin_action = context.user_data.get('admin_action')

    if admin_action == 'broadcast':
        text = update.message.text
        users = db.get_all_users()

        sent = 0
        failed = 0

        msg = await update.message.reply_text(f"📤 {len(users)} ta foydalanuvchiga yuborilmoqda...")

        for u in users:
            try:
                await context.bot.send_message(chat_id=u['user_id'], text=text)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await msg.edit_text(
            f"✅ Xabar yuborildi!\n\n"
            f"✅ Muvaffaqiyatli: {sent}\n"
            f"❌ Xato: {failed}"
        )
        context.user_data.pop('admin_action', None)
        return

    if admin_action == 'ban_by_id':
        try:
            uid = int(update.message.text)
            db.ban_user(uid)
            u = db.get_user(uid)
            name = u['first_name'] if u else uid
            await update.message.reply_text(
                f"🚫 {name} ({uid}) bloklandi!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Blokdan chiqarish", callback_data=f"unban_user_{uid}")]
                ])
            )
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID! Faqat raqam kiriting.")
        context.user_data.pop('admin_action', None)
        return

    if admin_action == 'search_user':
        try:
            uid = int(update.message.text)
            u = db.get_user(uid)
            if u:
                status_ban = "🚫 Bloklangan" if u.get('is_banned') else "✅ Faol"
                status_stop = "⏸ To'xtatilgan" if u.get('is_stopped') else ""
                results = db.get_user_results(uid)
                first_name = u.get('first_name', '')
                last_name = u.get('last_name', '')
                username_display = u.get('username') or "yo'q"
                joined = str(u['joined_at'])[:10]
                text = (
                    f"👤 <b>Foydalanuvchi:</b>\n"
                    f"🆔 ID: {u['user_id']}\n"
                    f"📛 Ism: {first_name} {last_name}\n"
                    f"🔗 Username: @{username_display}\n"
                    f"📅 Qo'shilgan: {joined}\n"
                    f"📊 Holat: {status_ban} {status_stop}\n"
                    f"🎮 Testlar: {len(results)} ta"
                )
                ban_btn = "↩️ Blokdan chiqarish" if u.get('is_banned') else "🚫 Bloklash"
                ban_cb = f"unban_user_{uid}" if u.get('is_banned') else f"ban_user_{uid}"
                stop_btn = "▶️ Botni yoqish" if u.get('is_stopped') else "⏸ Botni to'xtatish"
                stop_cb = f"unstop_user_{uid}" if u.get('is_stopped') else f"stop_user_{uid}"

                await update.message.reply_html(
                    text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(ban_btn, callback_data=ban_cb)],
                        [InlineKeyboardButton(stop_btn, callback_data=stop_cb)],
                    ])
                )
            else:
                await update.message.reply_text("❌ Foydalanuvchi topilmadi!")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!")
        context.user_data.pop('admin_action', None)
        return

    if admin_action == 'custom_date':
        try:
            parts = update.message.text.strip().split()
            if len(parts) == 2:
                start = parts[0]
                end = parts[1]
                stats = db.get_stats_custom_range(start, end)
                users = db.get_users_by_custom_range(start, end)
                text = (
                    f"📅 <b>{start} — {end}</b>\n\n"
                    f"👥 Yangi foydalanuvchilar: {stats['new_users']}\n"
                    f"🎮 O'yinlar: {stats['games']}\n"
                    f"📋 Yangi testlar: {stats.get('new_tests', 0)}\n\n"
                )
                if users:
                    text += "<b>Foydalanuvchilar:</b>\n"
                    for u in users[:20]:
                        text += f"• {u['first_name']} ({u['user_id']}) - {str(u['joined_at'])[:10]}\n"
                await update.message.reply_html(text)
            else:
                await update.message.reply_text("❌ Format: YYYY-MM-DD YYYY-MM-DD")
        except Exception as e:
            await update.message.reply_text(f"❌ Xato: {str(e)}")
        context.user_data.pop('admin_action', None)
        return

    if admin_action and admin_action.startswith('users_period_'):
        period = admin_action.replace('users_period_', '')
        users = db.get_users_by_period(period)
        await _show_users_list(update.message, users, period)
        context.user_data.pop('admin_action', None)
        return


async def _show_users_list(message, users, period_name):
    if not users:
        await message.reply_text("👥 Bu davrda foydalanuvchilar yo'q.")
        return

    text = f"👥 <b>Foydalanuvchilar ({period_name}, {len(users)} ta):</b>\n\n"
    for u in users[:30]:
        status = "🚫" if u.get('is_banned') else ("⏸" if u.get('is_stopped') else "✅")
        username = f"@{u['username']}" if u.get('username') else ""
        text += f"{status} {u['first_name']} {username}\n"
        text += f"   🆔 {u['user_id']} | 📅 {str(u['joined_at'])[:10]}\n\n"

    if len(users) > 30:
        text += f"... va yana {len(users) - 30} ta\n"

    if len(text) > 3500:
        text = text[:3500] + "..."

    await message.reply_html(text)


# ==================== COMMANDS ====================

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return

    if context.args:
        try:
            uid = int(context.args[0])
            db.ban_user(uid)
            u = db.get_user(uid)
            name = u['first_name'] if u else uid
            await update.message.reply_text(f"🚫 {name} ({uid}) bloklandi!")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!")
    else:
        context.user_data['admin_action'] = 'ban_by_id'
        await update.message.reply_text(
            "🚫 Bloklash uchun foydalanuvchi ID sini kiriting:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]])
        )


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return

    if context.args:
        try:
            uid = int(context.args[0])
            db.unban_user(uid)
            await update.message.reply_text(f"✅ Foydalanuvchi {uid} blokdan chiqarildi!")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!")
    else:
        await update.message.reply_text("Foydalanish: /unban <user_id>")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return

    if context.args:
        try:
            uid = int(context.args[0])
            db.stop_user(uid)
            await update.message.reply_text(f"⏸ Foydalanuvchi {uid} uchun bot to'xtatildi!")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!")
    else:
        await update.message.reply_text("Foydalanish: /stop <user_id>")


async def unstop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return

    if context.args:
        try:
            uid = int(context.args[0])
            db.unstop_user(uid)
            await update.message.reply_text(f"▶️ Foydalanuvchi {uid} uchun bot yoqildi!")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!")
    else:
        await update.message.reply_text("Foydalanish: /unstop <user_id>")


# ==================== USERS PERIOD CALLBACKS ====================

async def admin_users_period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if not is_admin(user.id):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await query.answer()
    action = query.data
    period = action.replace("admin_users_", "")

    if period == "custom":
        context.user_data['admin_action'] = 'custom_date_users'
        await query.edit_message_text(
            "📅 Sana oralig'ini kiriting:\nFormat: YYYY-MM-DD YYYY-MM-DD\nMisol: 2024-01-01 2024-12-31",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_users")]])
        )
        return

    users = db.get_users_by_period(period)
    text = f"👥 <b>Foydalanuvchilar ({period}, {len(users)} ta):</b>\n\n"

    for u in users[:25]:
        status = "🚫" if u.get('is_banned') else ("⏸" if u.get('is_stopped') else "✅")
        username = f"@{u['username']}" if u.get('username') else ""
        text += f"{status} {u['first_name']} {username}\n"
        text += f"   🆔 {u['user_id']} | 📅 {str(u['joined_at'])[:10]}\n\n"

    if len(users) > 25:
        text += f"... va yana {len(users) - 25} ta\n"

    if len(text) > 3500:
        text = text[:3500] + "..."

    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_users")]]

    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== MAIN TEXT HANDLER ====================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if db.is_banned(user.id) and user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz botdan bloklangansiz.")
        return

    if db.is_stopped(user.id) and user.id != ADMIN_ID:
        await update.message.reply_text("⏸ Bot siz uchun to'xtatilgan.")
        return

    if is_admin(user.id) and context.user_data.get('admin_action'):
        await handle_admin_message(update, context)
        return

    if context.user_data.get('adding_test'):
        await handle_test_creation(update, context)
        return

    if text == "📝 Testlar":
        await show_tests(update, context)
    elif text == "🏆 Reyting":
        await show_rating(update, context)
    elif text == "➕ Test qo'shish":
        await add_test_start(update, context)
    elif text == "📊 Mening natijalarim":
        await my_results(update, context)
    elif text == "🧮 Kalkulyator":
        await show_calculator(update, context)
    else:
        await handle_math_message(update, context)


# ==================== WEBAPP DATA ====================

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mini App dan kelgan ma'lumotlarni qayta ishlash"""
    data = update.effective_message.web_app_data.data
    try:
        payload = json.loads(data)
        action = payload.get('action')

        if action == 'add_test':
            user = update.effective_user
            questions = payload.get('questions', [])
            approved = is_admin(user.id)

            test_id = db.save_test(
                creator_id=user.id,
                title=payload['title'],
                description=payload.get('description', ''),
                questions=questions,
                approved=approved
            )

            status_word = "qo'shildi" if approved else "tasdiqlash kutmoqda"
            await update.message.reply_text(
                f"✅ Test muvaffaqiyatli {status_word}!"
            )

        elif action == 'calc':
            expr = payload.get('expr', '')
            result = safe_math_eval(expr)
            await update.message.reply_text(f"🧮 {expr} = {result}")

    except json.JSONDecodeError:
        await update.message.reply_text("❌ Ma'lumot xatosi!")


# ==================== MAIN ====================

async def set_commands(app: Application):
    commands = [
        BotCommand("start", "Botni boshlash"),
        BotCommand("tests", "Testlar ro'yxati"),
        BotCommand("addtest", "Test qo'shish"),
        BotCommand("rating", "Reyting ko'rish"),
        BotCommand("myresults", "Mening natijalarim"),
        BotCommand("calc", "Kalkulyator"),
        BotCommand("admin", "Admin panel (faqat admin)"),
        BotCommand("ban", "Foydalanuvchi bloklash (faqat admin)"),
        BotCommand("unban", "Blokdan chiqarish (faqat admin)"),
        BotCommand("stop", "Foydalanuvchi botni to'xtatish (faqat admin)"),
        BotCommand("unstop", "Foydalanuvchi botni yoqish (faqat admin)"),
    ]
    await app.bot.set_my_commands(commands)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tests", show_tests))
    app.add_handler(CommandHandler("addtest", add_test_start))
    app.add_handler(CommandHandler("rating", show_rating))
    app.add_handler(CommandHandler("myresults", my_results))
    app.add_handler(CommandHandler("calc", show_calculator))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("unstop", unstop_command))

    # Specific callback handlers (order matters!)
    app.add_handler(CallbackQueryHandler(test_info_callback, pattern=r"^test_info_\d+$"))
    app.add_handler(CallbackQueryHandler(start_test_callback, pattern=r"^start_test_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^answer_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(options_done_callback, pattern=r"^options_done$"))
    app.add_handler(CallbackQueryHandler(skip_description_callback, pattern=r"^skip_description$"))
    app.add_handler(CallbackQueryHandler(skip_explanation_callback, pattern=r"^skip_explanation$"))
    app.add_handler(CallbackQueryHandler(add_more_question_callback, pattern=r"^add_more_q$"))
    app.add_handler(CallbackQueryHandler(save_test_callback, pattern=r"^save_test$"))
    app.add_handler(CallbackQueryHandler(cancel_add_callback, pattern=r"^cancel_add$"))
    app.add_handler(CallbackQueryHandler(
        admin_users_period_callback,
        pattern=r"^admin_users_(today|week|month|3months|6months|year|all|custom)$"
    ))
    app.add_handler(CallbackQueryHandler(handle_calculator_callback, pattern=r"^calc_"))

    # General admin callback handler
    app.add_handler(CallbackQueryHandler(admin_panel_callback))

    # Message handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    app.post_init = set_commands

    logger.info("🤖 Quiz Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()