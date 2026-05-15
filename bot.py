import os
import json
import re
import asyncio
import threading
import logging
from flask import Flask
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ChatJoinRequestHandler, filters
)

# CONFIG (token environment থেকে নিন)
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
MAX_WARNS = 3
BAD_WORDS = ["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami",
             "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha",
             "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "মাগি", "magi",
             "ফালতু", "faltu", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor",
             "বেয়াদব", "beyadob", "লুচ্চা", "luccha", "খানকি", "khanki", "পোদ", "pod"]
EPISODE_KEYWORDS = ["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben",
                    "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"
BAD_WORD_PATTERN = re.compile(r'\b(?:' + '|'.join(map(re.escape, BAD_WORDS)) + r')\b')
EPISODE_PATTERN = re.compile(r'\b(?:' + '|'.join(map(re.escape, EPISODE_KEYWORDS)) + r')\b')

logging.basicConfig(level=logging.INFO)

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

async def is_admin(update):
    try:
        chat = update.effective_chat
        if not chat or chat.type == 'private':
            return False
        member = await chat.get_member(update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except Exception:
        return False

async def handle_message(update, context):
    if not update.message or not update.message.text:
        return
    if await is_admin(update):
        return

    text = update.message.text.lower()
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)

    # লিঙ্ক চেক
    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await update.message.reply_text("🔗 লিঙ্ক শেয়ার করা নিষেধ!")
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
                await update.message.reply_text("🚫 ৩ বার নিয়ম ভঙ্গের জন্য ব্যান করা হয়েছে।")
                db[chat_id][user_id] = 0
                save_data(db)
            except Exception as e:
                logging.error(f"Ban failed: {e}")
        else:
            await update.message.reply_text(f"⚠️ গালি নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        return

    # এপিসোড চেক
    if EPISODE_PATTERN.search(text):
        await update.message.reply_text("📢 এপিসোড খুব শীঘ্রই দেওয়া হবে!")

async def approve_join(update, context):
    req = update.chat_join_request
    await context.bot.approve_chat_join_request(req.chat.id, req.from_user.id)

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("বট সচল!")))
    application.add_handler(CommandHandler("rules", lambda u, c: u.message.reply_text("📜 নিয়ম: গালি নিষেধ, লিঙ্ক নিষেধ।")))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(ChatJoinRequestHandler(approve_join))

    print("Bot starting...")
    await application.run_polling()

if __name__ == "__main__":
    # Flask হেলথ চেক সার্ভার
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "Bot is running"
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}, daemon=True).start()

    # বট চালু
    asyncio.run(main())
