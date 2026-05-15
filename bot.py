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

# CONFIG
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
MAX_WARNS = 3
BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "মাগি", "magi", "ফালতু", "faltu", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "লুচ্চা", "luccha", "খানকি", "khanki", "পোদ", "pod"]
EPISODE_KEYWORDS =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"

logging.basicConfig(level=logging.INFO)

# DATA
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

db = load_data()

# ADMIN CHECK
async def is_admin(update):
    try:
        chat = update.effective_chat
        if not chat or chat.type == 'private': return False
        member = await chat.get_member(update.effective_user.id)
        return member.status in['creator', 'administrator']
    except: return False

# HANDLER
async def handle_message(u, c):
    if not u.message or not u.message.text: return
    if await is_admin(u): return
    
    text = u.message.text.lower()
    chat_id, user_id = str(u.effective_chat.id), str(u.effective_user.id)
    
    if re.search(LINK_REGEX, text):
        await u.message.delete()
        await u.message.reply_text("🔗 লিঙ্ক শেয়ার করা নিষেধ!")
        return

    if any(w in text for w in BAD_WORDS):
        await u.message.delete()
        if chat_id not in db: db[chat_id] = {}
        db[chat_id][user_id] = db[chat_id].get(user_id, 0) + 1
        warns = db[chat_id][user_id]
        save_data(db)
        if warns >= MAX_WARNS:
            await c.bot.ban_chat_member(u.effective_chat.id, user_id)
            await u.message.reply_text("🚫 ৩ বার নিয়ম ভঙ্গের জন্য ব্যান করা হয়েছে।")
            db[chat_id][user_id] = 0
            save_data(db)
        else:
            await u.message.reply_text(f"⚠️ গালি নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        return

    if any(k in text for k in EPISODE_KEYWORDS):
        await u.message.reply_text("📢 এপিসোড খুব শীঘ্রই দেওয়া হবে!")

# MAIN
if __name__ == "__main__":
    # Flask সার্ভার
    threading.Thread(target=lambda: Flask(__name__).run(host="0.0.0.0", port=8080), daemon=True).start()
    
    # Event Loop তৈরি করা (এরর সমাধানের মূল চাবিকাঠি)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = ApplicationBuilder().token(BOT_TOKEN).event_loop(loop).build()
    
    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("বট সচল!")))
    application.add_handler(CommandHandler("rules", lambda u, c: u.message.reply_text("📜 নিয়ম: গালি নিষেধ, লিঙ্ক নিষেধ।")))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(ChatJoinRequestHandler(lambda u, c: c.bot.approve_chat_join_request(u.chat_join_request.chat.id, u.chat_join_request.from_user.id)))
    
    print("Bot starting with manual loop...")
    application.run_polling()
