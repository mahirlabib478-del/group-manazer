import os
import json
import re
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ChatJoinRequestHandler, ContextTypes, filters
)

# =========================
# CONFIGURATION
# =========================
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
MAX_WARNS = 3

BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "মাগি", "magi", "ফালতু", "faltu", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "লুচ্চা", "luccha", "খানকি", "khanki", "পোদ", "pod"]
EPISODE_KEYWORDS =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"

logging.basicConfig(level=logging.INFO)

# =========================
# DATA STORAGE
# =========================
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

db = load_data()

# =========================
# UTILS & ADMIN CHECK
# =========================
async def is_admin(update: Update):
    if not update.effective_chat or update.effective_chat.type == 'private': return False
    try:
        admins = await update.effective_chat.get_administrators()
        return update.effective_user.id in [admin.user.id for admin in admins]
    except: return False

# =========================
# COMMANDS & MESSAGE HANDLERS
# =========================
async def start_cmd(u, c): await u.message.reply_text("✅ বট সচল আছে!")

async def rules_cmd(u, c): await u.message.reply_text("📜 নিয়মাবলী:\n১. গালিগালাজ নিষেধ।\n২. অনুমতি ছাড়া লিঙ্ক শেয়ার নিষেধ।\n৩. সকলকে সম্মান করুন।")

async def handle_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text: return
    if await is_admin(u): return # অ্যাডমিন হলে বট কোনো কাজ করবে না

    text = u.message.text.lower()
    chat_id, user_id = str(u.effective_chat.id), str(u.effective_user.id)
    username = u.effective_user.first_name

    # 1. লিঙ্ক ফিল্টার
    if re.search(LINK_REGEX, text):
        await u.message.delete()
        await u.message.reply_text(f"🔗 {username}, অনুমতি ছাড়া লিঙ্ক দেওয়া নিষেধ!")
        return

    # 2. ব্যাড ওয়ার্ড এবং ওয়ার্নিং সিস্টেম
    if any(w in text for w in BAD_WORDS):
        await u.message.delete()
        if chat_id not in db: db[chat_id] = {}
        if user_id not in db[chat_id]: db[chat_id][user_id] = 0
        
        db[chat_id][user_id] += 1
        warns = db[chat_id][user_id]
        save_data(db)
        
        if warns >= MAX_WARNS:
            await c.bot.ban_chat_member(u.effective_chat.id, user_id)
            await u.message.reply_text(f"🚫 {username} কে ৩ বার নিয়ম ভঙ্গের জন্য ব্যান করা হয়েছে।")
            db[chat_id][user_id] = 0
            save_data(db)
        else:
            await u.message.reply_text(f"⚠️ {username}, গালি দেওয়া নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        return

    # 3. এপিসোড কিওয়ার্ড
    if any(k in text for k in EPISODE_KEYWORDS):
        await u.message.reply_text("📢 আজকের এপিসোড খুব শীঘ্রই দেওয়া হবে, সাথে থাকুন!")

async def approve_join(u, c):
    await c.bot.approve_chat_join_request(u.chat_join_request.chat.id, u.chat_join_request.from_user.id)
    await c.bot.send_message(u.chat_join_request.chat.id, f"🎉 স্বাগতম {u.chat_join_request.from_user.first_name}!")

# =========================
# SERVER & APP
# =========================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Running"

def run_flask(): app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Flask সার্ভার চালু করা
    Thread(target=run_flask, daemon=True).start()
    
    # বট অ্যাপ্লিকেশন চালু করা
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("rules", rules_cmd))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(ChatJoinRequestHandler(approve_join))
    
    application.run_polling()
