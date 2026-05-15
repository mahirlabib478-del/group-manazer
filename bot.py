import os
import json
import re
import logging
from datetime import datetime, timedelta, timezone

from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import (
    Application,
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
BOT_TOKEN = "8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg"
DATA_FILE = "data.json"
BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]
EPISODE_KEYWORDS =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"
MAX_WARNS = 3

# LOGGING
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# DATA FUNCTIONS
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

data = load_data()

# KEEP ALIVE
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Running!"
def run(): app.run(host="0.0.0.0", port=8080)
def keep_alive(): Thread(target=run, daemon=True).start()

# IMAGE FUNCTION
def create_welcome_image(name, group_name, member_count):
    width, height = 1000, 500
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    # Background (Gradient)
    for y in range(height):
        draw.line([(0, y), (width, y)], fill=(int(40 + (y / height) * 80), int(80 + (y / height) * 100), int(180 + (y / height) * 50)))
    
    # Glow & Card
    img = img.filter(ImageFilter.GaussianBlur(12)).convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle((120, 90, 880, 410), radius=35, fill=(255, 255, 255, 45), outline=(255, 255, 255, 120), width=3)
    img = Image.alpha_composite(img, overlay)
    
    draw = ImageDraw.Draw(img)
    # Font handling
    font = ImageFont.load_default()
    
    draw.text((180, 130), "WELCOME", fill=(255, 255, 255))
    draw.text((180, 220), name, fill=(230, 240, 255))
    draw.text((180, 290), f"📛 {group_name}", fill=(255, 255, 255))
    draw.text((180, 340), f"👥 Members: {member_count}", fill=(220, 220, 220))
    
    path = "welcome.png"
    img.convert("RGB").save(path)
    return path

# LOGIC FUNCTIONS
async def is_admin(chat, user_id, context):
    admins = await context.bot.get_chat_administrators(chat.id)
    return user_id in [admin.user.id for admin in admins]

def get_user(chat_id, user_id):
    c, u = str(chat_id), str(user_id)
    if c not in data: data[c] = {}
    if u not in data[c]: data[c][u] = {"warns": 0, "links_allowed": False}
    return data[c][u]

async def add_warn(update, context, user_id):
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id, user_id)
    user_data["warns"] += 1
    save_data(data)
    
    await context.bot.send_message(chat_id, f"⚠️ Warning {user_data['warns']}/{MAX_WARNS}")
    
    if user_data["warns"] >= MAX_WARNS:
        until = datetime.now(timezone.utc) + timedelta(hours=24)
        await context.bot.ban_chat_member(chat_id, user_id, until_date=until)
        await context.bot.send_message(chat_id, "🚫 User banned for 24 hours!")
        user_data["warns"] = 0
        save_data(data)

# HANDLERS (Same as your logic, cleaned up)
#[এখানে আপনার আগের কমান্ড হ্যান্ডলার ফাংশনগুলো বসিয়ে নিন]

def main():
    keep_alive()
    bot = Application.builder().token(BOT_TOKEN).build()
    # Add your handlers here...
    bot.run_polling()

if __name__ == "__main__":
    main()
