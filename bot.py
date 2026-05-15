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
    ChatJoinRequestHandler, ContextTypes, filters
)

# =========================
# CONFIG & DATA
# =========================
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
MAX_WARNS = 3

BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "মাগি", "magi", "ফালতু", "faltu", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "লুচ্চা", "luccha", "খানকি", "khanki", "পোদ", "pod"]
EPISODE_KEYWORDS =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"

logging.basicConfig(level=logging.INFO)

# =========================
# UTILS & DATA
# =========================
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

data = load_data()

# এটিই সেই অ্যাডমিন ফাংশন যা আপনার বটের সুরক্ষা নিশ্চিত করবে
async def is_admin(update: Update):
    if not update.effective_chat or update.effective_chat.type == 'private': return False
    try:
        # বটের কাছে অ্যাডমিন লিস্ট চাওয়া
        admins = await update.effective_chat.get_administrators()
        admin_ids =[admin.user.id for admin in admins]
        return update.effective_user.id in admin_ids
    except: return False

# =========================
# HANDLERS
# =========================
async def start_cmd(u, c): await u.message.reply_text("✅ বট সক্রিয়!")

async def handle_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text: return
    
    # [গুরুত্বপূর্ণ] প্রতিটি মেসেজে আগে অ্যাডমিন চেক করা হচ্ছে
    if await is_admin(u): return 

    text = u.message.text.lower()
    chat_id, user_id = str(u.effective_chat.id), str(u.effective_user.id)
    username = u.effective_user.first_name

    # 1. লিঙ্ক ফিল্টার
    if re.search(LINK_REGEX, text):
        await u.message.delete()
        await u.message.reply_text(f"🔗 {username}, অনুমতি ছাড়া লিঙ্ক শেয়ার করা নিষেধ!")
        return

    # 2. ব্যাড ওয়ার্ড এবং ওয়ার্নিং সিস্টেম
    if any(w in text for w in BAD_WORDS):
        await u.message.delete()
        if chat_id not in data: data[chat_id] = {}
        if user_id not in data[chat_id]: data[chat_id][user_id] = 0
        
        data[chat_id][user_id] += 1
        warns = data[chat_id][user_id]
        save_data(data)
        
        if warns >= MAX_WARNS:
            await c.bot.ban_chat_member(u.effective_chat.id, user_id)
            await u.message.reply_text(f"🚫 {username}, ৩ বার নিয়ম ভঙ্গের জন্য ব্যান করা হয়েছে।")
            data[chat_id][user_id] = 0
            save_data(data)
        else:
            await u.message.reply_text(f"⚠️ {username}, গালি দেওয়া নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        return

    # 3. এপিসোড রিকোয়েস্ট
    if any(k in text for k in EPISODE_KEYWORDS):
        await u.message.reply_text("📢 এপিসোড খুব শীঘ্রই দেওয়া হবে, ধৈর্য ধরুন!")

async def join_req(u, c):
    await c.bot.approve_chat_join_request(u.chat_join_request.chat.id, u.chat_join_request.from_user.id)
    await c.bot.send_message(u.chat_join_request.chat.id, f"🎉 স্বাগতম {u.chat_join_request.from_user.first_name}!")

# =========================
# MAIN APP
# =========================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online"

async def run_bot():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start_cmd))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    bot_app.add_handler(ChatJoinRequestHandler(join_req))
    
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    await bot_app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()
    asyncio.run(run_bot())
