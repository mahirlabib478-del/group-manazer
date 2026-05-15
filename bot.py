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
# CONFIGURATION & DATA
# =========================
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
MAX_WARNS = 3

BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "মাগি", "magi", "ফালতু", "faltu", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "লুচ্চা", "luccha", "খানকি", "khanki", "পোদ", "pod"]
EPISODE_KEYWORDS =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"

logging.basicConfig(level=logging.INFO)

# =========================
# DATA MANAGEMENT (With Error Handling)
# =========================
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
    except Exception as e: logging.error(f"Save error: {e}")

data = load_data()

# =========================
# UTILS (Admin Check & User Data)
# =========================
async def is_admin(update: Update):
    if not update.effective_chat or update.effective_chat.type == 'private': return False
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except: return False

def get_user_warns(chat_id, user_id):
    c, u = str(chat_id), str(user_id)
    if c not in data: data[c] = {}
    if u not in data[c]: data[c][u] = 0
    return data[c][u]

# =========================
# HANDLERS
# =========================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বট সক্রিয় আছে!")

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 নিয়ম: গালি নিষেধ, লিঙ্ক নিষেধ।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if await is_admin(update): return # অ্যাডমিন হলে বট কোনো কাজ করবে না

    text = update.message.text.lower()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # 1. লিঙ্ক ফিল্টার
    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await update.message.reply_text("🔗 অনুমতি ছাড়া লিঙ্ক শেয়ার করা নিষেধ!")
        return

    # 2. ব্যাড ওয়ার্ড এবং ওয়ার্নিং
    if any(w in text for w in BAD_WORDS):
        await update.message.delete()
        warns = get_user_warns(chat_id, user_id) + 1
        data[str(chat_id)][str(user_id)] = warns
        save_data(data)
        
        if warns >= MAX_WARNS:
            await context.bot.ban_chat_member(chat_id, user_id)
            await update.message.reply_text(f"🚫 {update.effective_user.first_name} কে ৩ বার নিয়ম ভঙ্গের জন্য ব্যান করা হয়েছে।")
            data[str(chat_id)][str(user_id)] = 0 # রিসেট
            save_data(data)
        else:
            await update.message.reply_text(f"⚠️ {update.effective_user.first_name}, গালি দেওয়া নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        return

    # 3. এপিসোড রিকোয়েস্ট
    if any(k in text for k in EPISODE_KEYWORDS):
        await update.message.reply_text("📢 এপিসোড খুব শীঘ্রই দেওয়া হবে!")

async def join_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.approve_chat_join_request(update.chat_join_request.chat.id, update.chat_join_request.from_user.id)
    await context.bot.send_message(update.chat_join_request.chat.id, f"🎉 স্বাগতম {update.chat_join_request.from_user.first_name}!")

# =========================
# MAIN APP
# =========================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running"

async def run_bot():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start_cmd))
    bot_app.add_handler(CommandHandler("rules", rules_cmd))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    bot_app.add_handler(ChatJoinRequestHandler(join_req))
    
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    await bot_app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()
    asyncio.run(run_bot())
