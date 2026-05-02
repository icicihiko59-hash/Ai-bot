import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import OpenAI

# ---------------- CONFIG ----------------
TELEGRAM_TOKEN = "8134444233:AAGHsTKPj-HhHMqnIzJbSDcSev943FhSzSI"
OPENAI_API_KEY = "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"

ADMIN_ID = 8210146346

CHANNEL_1 = "@saniedit9"
CHANNEL_2 = "@primiumboss29"
FACEBOOK_PAGE = "https://www.facebook.com/profile.php?id=61589003704874"

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    limit_count INTEGER DEFAULT 10,
    mode TEXT DEFAULT 'chat',
    verified INTEGER DEFAULT 0,
    referred_by INTEGER,
    reward_given INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- DB HELPERS ----------------
def add_user(user_id, referred_by=None):
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (user_id, limit_count, mode, verified, referred_by, reward_given)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, 10, "chat", 0, referred_by, 0))
        conn.commit()

def get_limit(user_id):
    cur.execute("SELECT limit_count FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()[0]

def update_limit(user_id, amount=-1):
    cur.execute("UPDATE users SET limit_count = limit_count + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def set_mode(user_id, mode):
    cur.execute("UPDATE users SET mode=? WHERE user_id=?", (mode, user_id))
    conn.commit()

def get_mode(user_id):
    cur.execute("SELECT mode FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()[0]

def set_verified(user_id):
    cur.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
    conn.commit()

def is_verified(user_id):
    cur.execute("SELECT verified FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()[0] == 1

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_referrer(user_id):
    cur.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None

def reward_referrer(ref_id):
    if not ref_id:
        return

    cur.execute("SELECT reward_given FROM users WHERE user_id=?", (ref_id,))
    row = cur.fetchone()

    if row and row[0] == 0:
        cur.execute("UPDATE users SET limit_count = limit_count + 5 WHERE user_id=?", (ref_id,))
        cur.execute("UPDATE users SET reward_given = 1 WHERE user_id=?", (ref_id,))
        conn.commit()

# ---------------- OPENAI ----------------
def ask_ai(text, mode):
    system = "তুমি একজন সহায়ক বাংলা AI assistant। সবসময় বাংলায় উত্তর দাও।"

    if mode == "code":
        system = "তুমি একজন coding assistant। পরিষ্কার কোড + ব্যাখ্যা দাও।"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text}
        ]
    )
    return res.choices[0].message.content

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    referred_by = None
    if context.args:
        try:
            referred_by = int(context.args[0])
        except:
            referred_by = None

    add_user(user_id, referred_by)

    if not is_verified(user_id):

        keyboard = [
            [InlineKeyboardButton("📢 টেলিগ্রাম চ্যানেল ১", url=f"https://t.me/{CHANNEL_1.replace('@','')}")],
            [InlineKeyboardButton("📢 টেলিগ্রাম চ্যানেল ২", url=f"https://t.me/{CHANNEL_2.replace('@','')}")],
            [InlineKeyboardButton("👍 ফেসবুক পেজ", url=FACEBOOK_PAGE)],
            [InlineKeyboardButton("✅ ভেরিফাই করুন", callback_data="verify")]
        ]

        await update.message.reply_text(
            "🚨 বট ব্যবহার করতে নিচেরগুলো জয়েন করুন:\n\n"
            "✔ টেলিগ্রাম চ্যানেল ১\n"
            "✔ টেলিগ্রাম চ্যানেল ২\n"
            "✔ ফেসবুক পেজ\n\n"
            "তারপর ‘ভেরিফাই’ চাপুন 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    link = f"https://t.me/{context.bot.username}?start={user_id}"

    keyboard = [
        ["💬 চ্যাট মোড", "💻 কোড মোড"],
        ["📊 আমার লিমিট", "🔗 রেফারেল লিংক"]
    ]

    await update.message.reply_text(
        "🤖 স্বাগতম!\n🇧🇩 বাংলা AI Bot প্রস্তুত\n\n"
        f"🔗 আপনার রেফারেল লিংক:\n{link}",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---------------- VERIFY ----------------
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    await query.edit_message_text("⏳ যাচাই করা হচ্ছে...")

    set_verified(user_id)

    ref = get_referrer(user_id)
    reward_referrer(ref)

    await query.message.reply_text("✅ ভেরিফিকেশন সফল!\nএখন আপনি বট ব্যবহার করতে পারবেন 🇧🇩")

# ---------------- HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    add_user(user_id)

    if not is_verified(user_id):
        await update.message.reply_text("❌ আগে /start দিয়ে ভেরিফাই করুন")
        return

    if text == "💬 চ্যাট মোড":
        set_mode(user_id, "chat")
        await update.message.reply_text("💬 চ্যাট মোড চালু হয়েছে")
        return

    if text == "💻 কোড মোড":
        set_mode(user_id, "code")
        await update.message.reply_text("💻 কোড মোড চালু হয়েছে")
        return

    if text == "📊 আমার লিমিট":
        await update.message.reply_text(f"⛔ আপনার লিমিট: {get_limit(user_id)}")
        return

    if text == "🔗 রেফারেল লিংক":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(f"🔗 আপনার রেফারেল লিংক:\n{link}")
        return

    limit = get_limit(user_id)

    if not is_admin(user_id) and limit <= 0:
        await update.message.reply_text("❌ আপনার লিমিট শেষ হয়ে গেছে!")
        return

    if not is_admin(user_id):
        update_limit(user_id, -1)

    mode = get_mode(user_id)
    reply = ask_ai(text, mode)

    await update.message.reply_text(
        f"🤖 উত্তর:\n{reply}\n\n⛔ লিমিট: {get_limit(user_id)}"
    )

# ---------------- RUN ----------------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🤖 বাংলা AI Bot চালু হয়েছে...")
app.run_polling()