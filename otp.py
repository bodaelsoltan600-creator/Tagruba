import telebot
import secrets
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ================== CONFIG ==================
BOT_TOKEN = "8443058893:AAEJVazU7cVE-k4QHWCYQ_ZkKmzUIsxg0MI"
OTP_EXPIRY_SECONDS = 60
MAX_ATTEMPTS = 3
# ============================================

bot = telebot.TeleBot(BOT_TOKEN)

# تخزين الجلسات مؤقتًا
sessions = {}

# ---------- HELPERS ----------

def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    start = phone[:4]
    end = phone[-2:]
    masked = "*" * (len(phone) - 6)
    return f"{start}{masked}{end}"

# ---------- OTP LOGIC ----------

def create_otp_session(user_id: int, phone: str):
    otp = f"{secrets.randbelow(10**6):06d}"
    return {
        "phone": phone,
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(seconds=OTP_EXPIRY_SECONDS),
        "attempts": 0,
        "used": False
    }

def verify_otp(session, entered_otp: str):
    if session["used"]:
        return "OTP_ALREADY_USED"

    if datetime.utcnow() > session["expires_at"]:
        return "OTP_EXPIRED"

    if session["attempts"] >= MAX_ATTEMPTS:
        return "TOO_MANY_ATTEMPTS"

    session["attempts"] += 1

    if entered_otp == session["otp"]:
        session["used"] = True
        return "OTP_VALID"

    return "OTP_INVALID"

# ---------- BOT HANDLERS ----------

@bot.message_handler(commands=["start"])
def start(message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True))

    bot.send_message(
        message.chat.id,
        "📞 من فضلك شارك رقمك لبدء التحقق",
        reply_markup=kb
    )

@bot.message_handler(content_types=["contact"])
def receive_phone(message):
    user_id = message.from_user.id
    phone = message.contact.phone_number

    session = create_otp_session(user_id, phone)
    sessions[user_id] = session

    masked_phone = mask_phone(phone)

    bot.send_message(
        message.chat.id,
        f"""
🔐 Verification Code Generated

📱 Phone: {masked_phone}
🔢 OTP (تعليمي): `{session['otp']}`

⏳ Valid for {OTP_EXPIRY_SECONDS} seconds
❌ Max attempts: {MAX_ATTEMPTS}

✍️ اكتب الكود الآن

⚠️ Internal verification only
""",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_otp_input(message):
    user_id = message.from_user.id
    entered_otp = message.text.strip()

    if user_id not in sessions:
        bot.send_message(
            message.chat.id,
            "❗ لا توجد جلسة نشطة\nاكتب /start للبدء"
        )
        return

    session = sessions[user_id]
    result = verify_otp(session, entered_otp)

    if result == "OTP_VALID":
        bot.send_message(message.chat.id, "✅ تم التحقق بنجاح")
        sessions.pop(user_id)

    elif result == "OTP_INVALID":
        remaining = MAX_ATTEMPTS - session["attempts"]
        bot.send_message(
            message.chat.id,
            f"❌ كود غير صحيح\n🔁 محاولات متبقية: {remaining}"
        )

    elif result == "OTP_EXPIRED":
        bot.send_message(
            message.chat.id,
            "⏳ انتهت صلاحية الكود\nاكتب /start لإنشاء كود جديد"
        )
        sessions.pop(user_id)

    elif result == "TOO_MANY_ATTEMPTS":
        bot.send_message(
            message.chat.id,
            "🚫 تم تجاوز عدد المحاولات\nاكتب /start"
        )
        sessions.pop(user_id)

# ---------- RUN ----------
bot.infinity_polling()