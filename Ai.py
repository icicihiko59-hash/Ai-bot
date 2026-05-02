import os
import sqlite3
import openai
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ---------------- CONFIG (ENV SAFE) ----------------
TELEGRAM_TOKEN = os.getenv("8134444233:AAGHsTKPj-HhHMqnIzJbSDcSev943FhSzSI")
OPENAI_API_KEY = os.getenv("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")

openai.api_key = OPENAI_API_KEY

ADMIN_ID = 8210146346

CHANNEL_1 = "@saniedit9"
CHANNEL_2 = "@primiumboss29"
FACEBOOK_PAGE = "https://www.facebook.com/profile.php?id=61589003704874"

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
    row = cur.fetchone()
    return row[0] if row else 0

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
    row = cur.fetchone()
    return row and row[0] == 1

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

# ---------------- AI FUNCTION ----------------
def ask_ai(text, mode):
    system = "তুমি একজন সহায়ক বাংলা AI assistant। সবসময় বাংলায় উত্তর দাও।"

    if mode == "code":
        system = "তুমি একজন coding assistant। পরিষ্কার কোড দাও এবং ব্যাখ্যা করো।"

    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text}
        ]
    )

    return res["choices"][0]["message"]["content"]

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
            [InlineKeyboardButton("📢 Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@','')}")],
            [InlineKeyboardButton("📢 Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@','')}")],
            [InlineKeyboardButton("👍 Facebook Page", url=FACEBOOK_PAGE)],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]

        await update.message.reply_text(
            "🚨 Bot ব্যবহার করতে নিচেরগুলো join করুন:\n\n"
            "✔ Channel 1\n✔ Channel 2\n✔ Facebook Page\n\n"
            "তারপর Verify চাপুন 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    link = f"https://t.me/{context.bot.username}?start={user_id}"

    keyboard = [
        ["💬 চ্যাট মোড", "💻 কোড মোড"],
        ["📊 আমার লিমিট", "🔗 রেফারেল লিংক"]
    ]

    await update.message.reply_text(
        "🤖 বাংলা AI Bot প্রস্তুত 🇧🇩\n\n"
        f"🔗 আপনার রেফারেল লিংক:\n{link}",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---------------- VERIFY ----------------
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    set_verified(user_id)

    ref = get_referrer(user_id)
    reward_referrer(ref)

    await query.message.reply_text("✅ Verification Successful!\nএখন আপনি bot ব্যবহার করতে পারবেন 🇧🇩")

# ---------------- MESSAGE HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    add_user(user_id)

    if not is_verified(user_id):
        await update.message.reply_text("❌ আগে /start দিয়ে verify করুন")
        return

    if text == "💬 চ্যাট মোড":
        set_mode(user_id, "chat")
        await update.message.reply_text("💬 Chat Mode ON")
        return

    if text == "💻 কোড মোড":
        set_mode(user_id, "code")
        await update.message.reply_text("💻 Code Mode ON")
        return

    if text == "📊 আমার লিমিট":
        await update.message.reply_text(f"⛔ আপনার লিমিট: {get_limit(user_id)}")
        return

    if text == "🔗 রেফারেল লিংক":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(f"🔗 আপনার লিংক:\n{link}")
        return

    limit = get_limit(user_id)

    if not is_admin(user_id) and limit <= 0:
        await update.message.reply_text("❌ আপনার লিমিট শেষ!")
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

print("🤖 Bot Running...")
app.run_polling()
