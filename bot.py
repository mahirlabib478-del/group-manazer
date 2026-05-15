import os
import json
import re
import asyncio
import threading
import logging
from io import BytesIO
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ChatJoinRequestHandler, filters, ContextTypes
)
from telegram.error import BadRequest, Forbidden
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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

# ফন্ট সেটআপ
FONT_PATH = "NotoSerifBengali-Regular.ttf"  # প্রজেক্টে রাখা ফন্ট ফাইলের নাম
try:
    bengali_font = ImageFont.truetype(FONT_PATH, 40)
    small_font = ImageFont.truetype(FONT_PATH, 24)
except:
    # ফাইল না থাকলে ডিফল্ট ইংরেজি ফন্ট (বাংলা সাপোর্ট করবে না)
    bengali_font = ImageFont.load_default()
    small_font = ImageFont.load_default()

# অ্যাডমিন চেক
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat = update.effective_chat
        if not chat or chat.type == 'private':
            return False
        user_id = update.effective_user.id
        member = await context.bot.get_chat_member(chat.id, user_id)
        return member.status in ['creator', 'administrator']
    except (BadRequest, Forbidden) as e:
        logging.warning(f"is_admin check failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error in is_admin: {e}")
        return False

async def send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"send_message failed: {e}")

# ===== ইমেজ জেনারেটর =====
def generate_welcome_image(member_name: str, group_name: str) -> BytesIO:
    # আর্টবোর্ড সাইজ
    W, H = 800, 400

    # গাঢ় গ্রেডিয়েন্ট ব্যাকগ্রাউন্ড
    img = Image.new("RGB", (W, H), "#1A1A2E")
    draw = ImageDraw.Draw(img)
    for i in range(H):
        r = int(26 + (i / H) * 20)   # 26 → 46
        g = int(26 + (i / H) * 10)   # 26 → 36
        b = int(46 + (i / H) * 30)   # 46 → 76
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    # মাঝখানে একটি উজ্জ্বল ওভারলে প্যানেল (গ্লাস ইফেক্ট)
    panel = Image.new("RGBA", (600, 250), (255, 255, 255, 30))
    img.paste(panel, (100, 75), panel)

    # ডেকোরেটিভ গোল্ডেন বর্ডার
    draw.rectangle([(100, 75), (700, 325)], outline="#F1C40F", width=3)

    # টাইটেল: স্বাগতম
    try:
        title_font = ImageFont.truetype(FONT_PATH, 48)
        name_font = ImageFont.truetype(FONT_PATH, 36)
        group_font = ImageFont.truetype(FONT_PATH, 24)
    except:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        group_font = ImageFont.load_default()

    draw.text((W//2, 130), "✨ স্বাগতম! ✨", fill="#F1C40F", font=title_font, anchor="mm")

    # সদস্যের নাম (বড়, সাদা)
    draw.text((W//2, 200), f"👤 {member_name}", fill="#FFFFFF", font=name_font, anchor="mm")

    # গ্রুপের নাম (ছোট, ধূসর)
    group_display = group_name if group_name else "আমাদের গ্রুপ"
    draw.text((W//2, 270), f"🏠 {group_display}", fill="#BDC3C7", font=group_font, anchor="mm")

    # নিচে একটি সোনালী লাইন
    draw.rectangle([(250, 340), (550, 345)], fill="#F1C40F")

    # প্রোফাইল ছবি যোগ করতে চাইলে (অপশনাল)
    # সদস্যের প্রোফাইল ফটো ডাউনলোড করে এখানে পেস্ট করতে পারেন

    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio
# ===== হ্যান্ডলার =====
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        # ছবি তৈরি
        image_data = generate_welcome_image(member.full_name, chat.title)
        # ছবি পাঠান
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=image_data,
            caption=f"🎉 {member.full_name} কে স্বাগতম!\nনিয়ম মেনে চলার অনুরোধ রইল।"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await is_admin(update, context):
        return

    text = update.message.text.lower()
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)

    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await send_message(context, update.effective_chat.id, "🔗 লিঙ্ক শেয়ার করা নিষেধ!")
        return

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

    if EPISODE_PATTERN.search(text):
        await send_message(context, update.effective_chat.id, "📢 এপিসোড খুব শীঘ্রই দেওয়া হবে!")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.delete()
        await send_message(context, update.effective_chat.id, "⛔ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য!")
        return
    await send_message(context, update.effective_chat.id, "👑 অ্যাডমিন প্যানেল:\nআপনার অনুমতি আছে।")

async def catch_command_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await is_admin(update, context):
        return
    text = update.message.text
    if re.search(LINK_REGEX, text):
        await update.message.delete()
        await send_message(context, update.effective_chat.id, "🔗 কমান্ডের সাথে লিঙ্ক শেয়ার নিষেধ!")

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

    # ইভেন্ট লুপ তৈরি ও সেট (Python 3.14-এর জন্য জরুরি)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # টেলিগ্রাম বট অ্যাপ্লিকেশন
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", ...))
    application.add_handler(CommandHandler("rules", ...))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(ChatJoinRequestHandler(approve_join))
    application.add_handler(MessageHandler(filters.COMMAND, catch_command_links))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot starting...")
    application.run_polling()  # ইভেন্ট লুপ থাকায় ঠিক চলবে
