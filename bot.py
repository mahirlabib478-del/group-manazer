import os
import json
import re
import logging
import asyncio
import threading
from flask import Flask
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ChatJoinRequestHandler,
    filters
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================
# CONFIG
# =========================
# সতর্কতা: টোকেনটি পরিবর্তন করে নিন
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]
EPISODE_KEYWORDS =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"
MAX_WARNS = 3

# LOGGING
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# DATA
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

data = load_data()

# FLASK KEEP ALIVE
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# IMAGE GENERATOR
def create_welcome_image(name, group_name, member_count):
    # (আপনার আগের কোড অনুযায়ী ইমেজ ফাংশনটি এখানে থাকবে)
    # ফন্ট এবং গ্রাফিক্সের জন্য ইমেজ লজিক এখানে ব্যবহার করুন
    return "welcome.png" 

# HANDLERS (Simplified)
async def is_admin(chat, user_id, context):
    admins = await context.bot.get_chat_administrators(chat.id)
    return user_id in [admin.user.id for admin in admins]

def get_user(chat_id, user_id):
    c, u = str(chat_id), str(user_id)
    if c not in data: data[c] = {}
    if u not in data[c]: data[c][u] = {"warns": 0, "links_allowed": False}
    return data[c][u]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (আপনার আগের মেসেজ হ্যান্ডলার লজিক এখানে বসান)
    pass

# MAIN RUNNER
async def run_bot():
    bot = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    bot.add_handler(CommandHandler("rules", lambda u, c: u.message.reply_text("📜 Group Rules...")))
    # Add other handlers here...

    # Messages & Join
    bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot Polling Starting...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    
    # Run forever
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Flask কে আলাদা থ্রেডে চালু করা
    threading.Thread(target=run_flask, daemon=True).start()
    
    # বটকে asyncio লুপে চালু করা
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"Error: {e}")
