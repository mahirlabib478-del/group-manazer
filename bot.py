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
from PIL import Image, ImageDraw, ImageFont

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

# ডেটা লোড/সেভ
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

data = load_data()

# অ্যাডমিন চেক ফাংশন
async def is_admin(update: Update):
    chat_member = await update.effective_chat.get_member(update.effective_user.id)
    return chat_member.status in ['creator', 'administrator']

# ইউজার ডেটা ম্যানেজমেন্ট
def get_user_data(chat_id, user_id):
    c, u = str(chat_id), str(user_id)
    if c not in data: data[c] = {}
    if u not in data[c]: data[c][u] = {"warns": 0}
    return data[c][u]

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বট সক্রিয় আছে! আপনার গ্রুপ ম্যানেজমেন্টের জন্য প্রস্তুত।")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 গ্রুপ নিয়মাবলী:\n১. গালিগালাজ নিষেধ।\n২. অনুমতি ছাড়া লিঙ্ক শেয়ার করবেন না।\n৩. সকলকে সম্মান করুন।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    # যদি অ্যাডমিন হয়, বট হস্তক্ষেপ করবে না
    if await is_admin(update): return

    text = update.message.text.lower()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_data = get_user_data(chat_id, user_id)

    # ১. ব্যাড ওয়ার্ড ফিল্টার
    if any(word in text for word in BAD_WORDS):
        await update.message.delete()
        user_data["warns"] += 1
        save_data(data)
        warns = user_data["warns"]
        await update.message.reply_text(f"⚠️ {update.effective_user.first_name}, গালি দেওয়া নিষেধ! ওয়ার্নিং: {warns}/{MAX_WARNS}")
        
        if warns >= MAX_WARNS:
            await context.bot.ban_chat_member(chat_id, user_id)
            await update.message.reply_text(f"🚫 {update.effective_user.first_name} কে ব্যান করা হয়েছে।")
        return

    # ২. লিঙ্ক ফিল্টার
    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await update.message.reply_text("🔗 অনুমতি ছাড়া লিঙ্ক শেয়ার করা নিষেধ!")
        return

    # ৩. এপিসোড কিওয়ার্ড
    if any(keyword in text for keyword in EPISODE_KEYWORDS):
        await update.message.reply_text("📢 আজকের এপিসোড খুব শীঘ্রই দেওয়া হবে, ধৈর্য ধরুন!")

async def approve_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    await context.bot.approve_chat_join_request(request.chat.id, request.from_user.id)
    await context.bot.send_message(
        chat_id=request.chat.id, 
        text=f"🎉 স্বাগতম {request.from_user.first_name}! আমাদের গ্রুপে জয়েন করার জন্য ধন্যবাদ।"
    )

# =========================
# MAIN APP
# =========================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running"

async def main():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("rules", rules))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    bot_app.add_handler(ChatJoinRequestHandler(approve_join_request))
    
    # Background Flask
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()
    
    print("Bot is polling...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
