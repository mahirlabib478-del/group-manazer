import os
import json
import re
import asyncio
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ChatJoinRequestHandler, filters, ContextTypes
)
from telegram.error import BadRequest, Forbidden

# কনফিগ
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
MAX_WARNS = 3

BAD_WORDS = [
    "শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami",
    "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha",
    "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "মাগি", "magi",
    "ফালতু", "faltu", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor",
    "বেয়াদব", "beyadob", "লুচ্চা", "luccha", "খানকি", "khanki", "পোদ", "pod"
]
EPISODE_KEYWORDS = [
    "episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben",
    "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"
]

LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"
BAD_WORD_PATTERN = re.compile(r'\b(?:' + '|'.join(map(re.escape, BAD_WORDS)) + r')\b')
EPISODE_PATTERN = re.compile(r'\b(?:' + '|'.join(map(re.escape, EPISODE_KEYWORDS)) + r')\b')

logging.basicConfig(level=logging.INFO)

# ডেটা ম্যানেজমেন্ট
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

db = load_data()

# অ্যাডমিন চেক (উন্নত + লগিং)
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat = update.effective_chat
        if not chat or chat.type == 'private':
            return False
        user_id = update.effective_user.id
        # সরাসরি get_chat_member ব্যবহার করা (context থেকে বট পাওয়া যায়)
        member = await context.bot.get_chat_member(chat.id, user_id)
        return member.status in ['creator', 'administrator']
    except (BadRequest, Forbidden) as e:
        logging.warning(f"is_admin check failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error in is_admin: {e}")
        return False

# মেসেজ পাঠানোর সেফ ফাংশন
async def send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"send_message failed: {e}")

# ===== হ্যান্ডলারগুলো =====

# সাধারণ টেক্সট মেসেজ (লিংক, গালি, এপিসোড) – শুধু অ্যাডমিন বাদে
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await is_admin(update, context):
        return

    text = update.message.text.lower()
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)

    # লিংক চেক
    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await send_message(context, update.effective_chat.id, "🔗 লিঙ্ক শেয়ার করা নিষেধ!")
        return

    # গালি চেক
    if BAD_WORD_PATTERN.search(text):
        await update.message.delete()
        if chat_id not in db:
            db[chat_id] = {}
        db[chat_id][user_id] = db[chat_id].get(user_id, 0) + 1
        warns = db[chat_id][user_id]
        save_data(db)
        if warns >= MAX_WARNS:
            try:
                await context.bot.ban_chat_member(update.effective_chat.id, user_id)
                await send_message(context, update.effective_chat.id, f"🚫 {update.effective_user.full_name} ৩ বার নিয়ম ভঙ্গ করায় ব্যান করা হয়েছে।")
                db[chat_id][user_id] = 0
                save_data(db)
            except Exception as e:
                logging.error(f"Ban failed: {e}")
        else:
            await send_message(context, update.effective_chat.id, f"⚠️ {update.effective_user.full_name} গালি নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        return

    # এপিসোড রিমাইন্ডার
    if EPISODE_PATTERN.search(text):
        await send_message(context, update.effective_chat.id, "📢 এপিসোড খুব শীঘ্রই দেওয়া হবে!")

# /admin কমান্ড – শুধুমাত্র অ্যাডমিনের জন্য
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.delete()
        await send_message(context, update.effective_chat.id, "⛔ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য!")
        return
    await send_message(context, update.effective_chat.id, "👑 অ্যাডমিন প্যানেল:\nআপনার অনুমতি আছে।")

# যেকোনো কমান্ডের ভেতর লিংক চেক (যেমন /blah https://link)
async def catch_command_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    # যদি অ্যাডমিন হয়, কিছু করব না
    if await is_admin(update, context):
        return

    text = update.message.text
    # লিংক খোঁজা
    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await send_message(context, update.effective_chat.id, "🔗 কমান্ডের সাথে লিঙ্ক শেয়ার নিষেধ!")
        # ইচ্ছা করলে ওয়ার্নিংও দিতে পারেন
        # ওয়ার্নিং লজিক এখানে কল করতে পারেন

# ওয়েলকাম মেসেজ
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await send_message(context, update.effective_chat.id, f"👋 স্বাগতম {member.full_name}!\nদয়া করে গ্রুপের নিয়ম মেনে চলুন।")

# জয়েন রিকোয়েস্ট অ্যাপ্রুভ
async def approve_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    await context.bot.approve_chat_join_request(req.chat.id, req.from_user.id)

# ===== মেইন =====
if __name__ == "__main__":
    # Flask হেলথচেক
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "Bot is running"
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": 8080},
        daemon=True
    ).start()

    # ইভেন্ট লুপ (Python 3.14 ফিক্স)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # নির্দিষ্ট কমান্ড হ্যান্ডলার
    application.add_handler(CommandHandler("start", lambda u, c: send_message(c, u.effective_chat.id, "বট সচল!")))
    application.add_handler(CommandHandler("rules", lambda u, c: send_message(c, u.effective_chat.id, "📜 নিয়ম:\n- গালি নিষেধ\n- লিঙ্ক শেয়ার নিষেধ\n- এপিসোডের জন্য বারবার জিজ্ঞাসা নিষেধ")))
    application.add_handler(CommandHandler("admin", admin_command))

    # নতুন সদস্য ওয়েলকাম
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # জয়েন রিকোয়েস্ট
    application.add_handler(ChatJoinRequestHandler(approve_join))

    # যেকোনো কমান্ডের ভেতর লিংক ধরা (সবার শেষে, যাতে start/rules/admin ইত্যাদি আগে ধরা পড়ে)
    application.add_handler(MessageHandler(filters.COMMAND, catch_command_links))

    # সাধারণ টেক্সট
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot starting...")
    application.run_polling()
