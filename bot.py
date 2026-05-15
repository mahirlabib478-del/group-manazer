import os
import json
import re
import logging
from datetime import datetime, timedelta

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

from PIL import Image, ImageDraw, ImageFont

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("8954395264:AAF5qQGo83So7AezJB-ShloYjbGijr25tLg")

DATA_FILE = "data.json"

BAD_WORDS = ["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]

EPISODE_KEYWORDS = ["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]

LINK_REGEX = r"(https?://\S+|t\.me/\S+|@\w+)"

MAX_WARNS = 3

# =========================
# LOGGING
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# =========================
# DATA
# =========================

def load_data():

    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

data = load_data()

# =========================
# KEEP ALIVE
# =========================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =========================
# IMAGE
# =========================

def create_welcome_image(name, group_name, member_count):

    from PIL import ImageFilter

    width = 1000
    height = 500

    img = Image.new("RGB", (width, height))

    draw = ImageDraw.Draw(img)

    # Gradient Background
    for y in range(height):

        r = int(40 + (y / height) * 80)
        g = int(80 + (y / height) * 100)
        b = int(180 + (y / height) * 50)

        draw.line(
            [(0, y), (width, y)],
            fill=(r, g, b)
        )

    # Glow
    draw.ellipse(
        (700, 50, 980, 330),
        fill=(255, 120, 255)
    )

    draw.ellipse(
        (50, 250, 350, 550),
        fill=(120, 200, 255)
    )

    img = img.filter(
        ImageFilter.GaussianBlur(12)
    )

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    overlay_draw = ImageDraw.Draw(overlay)

    # Glass Card
    overlay_draw.rounded_rectangle(
        (120, 90, 880, 410),
        radius=35,
        fill=(255, 255, 255, 45),
        outline=(255, 255, 255, 120),
        width=3
    )

    img = img.convert("RGBA")

    img = Image.alpha_composite(
        img,
        overlay
    )

    draw = ImageDraw.Draw(img)

    try:

        big_font = ImageFont.truetype(
            "arial.ttf",
            58
        )

        small_font = ImageFont.truetype(
            "arial.ttf",
            34
        )

        mini_font = ImageFont.truetype(
            "arial.ttf",
            28
        )

    except:

        big_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        mini_font = ImageFont.load_default()

    # Welcome
    draw.text(
        (180, 130),
        "WELCOME",
        font=big_font,
        fill=(255, 255, 255)
    )

    # Name
    draw.text(
        (180, 220),
        name,
        font=small_font,
        fill=(230, 240, 255)
    )

    # Group
    draw.text(
        (180, 290),
        f"📛 {group_name}",
        font=mini_font,
        fill=(255, 255, 255)
    )

    # Members
    draw.text(
        (180, 340),
        f"👥 Members: {member_count}",
        font=mini_font,
        fill=(220, 220, 220)
    )

    path = "welcome.png"

    img.save(path)

    return path

# =========================
# HELPERS
# =========================

async def is_admin(chat, user_id, context):

    admins = await context.bot.get_chat_administrators(
        chat.id
    )

    admin_ids = [
        admin.user.id
        for admin in admins
    ]

    return user_id in admin_ids

def get_user(chat_id, user_id):

    chat_id = str(chat_id)
    user_id = str(user_id)

    if chat_id not in data:
        data[chat_id] = {}

    if user_id not in data[chat_id]:

        data[chat_id][user_id] = {
            "warns": 0,
            "links_allowed": False
        }

    return data[chat_id][user_id]

# =========================
# WARN SYSTEM
# =========================

async def add_warn(update, context, user_id):

    chat_id = update.effective_chat.id

    user_data = get_user(chat_id, user_id)

    user_data["warns"] += 1

    save_data(data)

    warns = user_data["warns"]

    await context.bot.send_message(
        chat_id,
        f"⚠️ Warning {warns}/{MAX_WARNS}"
    )

    if warns >= MAX_WARNS:

        until = datetime.utcnow() + timedelta(hours=24)

        try:

            await context.bot.ban_chat_member(
                chat_id,
                user_id,
                until_date=until
            )

            await context.bot.send_message(
                chat_id,
                "🚫 User banned for 24 hours!"
            )

            user_data["warns"] = 0

            save_data(data)

        except Exception as e:
            print(e)

# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    message = update.message
    chat = message.chat
    user = message.from_user

    text = (
        message.text or
        message.caption or
        ""
    ).lower()

    if not text:
        return

    admin = await is_admin(
        chat,
        user.id,
        context
    )

    # BAD WORD
    if any(word in text for word in BAD_WORDS):

        if not admin:

            try:
                await message.delete()
            except:
                pass

            await add_warn(
                update,
                context,
                user.id
            )

        return

    # LINKS
    if re.search(LINK_REGEX, text):

        user_data = get_user(
            chat.id,
            user.id
        )

        if not admin and not user_data["links_allowed"]:

            try:
                await message.delete()
            except:
                pass

            await context.bot.send_message(
                chat.id,
                "🔗 Link not allowed!"
            )

        return

    # EPISODE
    if any(word in text for word in EPISODE_KEYWORDS):

        await context.bot.send_message(
            chat.id,
            "📢 Episode update soon!"
        )

# =========================
# COMMANDS
# =========================

async def rules(update, context):

    text = """
📜 Group Rules

1. No bad words
2. No spam
3. No links without permission
4. Respect everyone
"""

    await update.message.reply_text(text)

async def stats(update, context):

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    user_data = get_user(
        chat_id,
        user_id
    )

    await update.message.reply_text(
        f"📊 Warnings: {user_data['warns']}"
    )

async def warn(update, context):

    admin = await is_admin(
        update.effective_chat,
        update.effective_user.id,
        context
    )

    if not admin:
        return

    if not update.message.reply_to_message:

        await update.message.reply_text(
            "Reply to user message"
        )

        return

    target = update.message.reply_to_message.from_user

    await add_warn(
        update,
        context,
        target.id
    )

async def unwarn(update, context):

    admin = await is_admin(
        update.effective_chat,
        update.effective_user.id,
        context
    )

    if not admin:
        return

    if not update.message.reply_to_message:
        return

    target = update.message.reply_to_message.from_user

    user_data = get_user(
        update.effective_chat.id,
        target.id
    )

    user_data["warns"] = max(
        0,
        user_data["warns"] - 1
    )

    save_data(data)

    await update.message.reply_text(
        "✅ Warning removed"
    )

async def allowlink(update, context):

    admin = await is_admin(
        update.effective_chat,
        update.effective_user.id,
        context
    )

    if not admin:
        return

    if not update.message.reply_to_message:
        return

    target = update.message.reply_to_message.from_user

    user_data = get_user(
        update.effective_chat.id,
        target.id
    )

    user_data["links_allowed"] = True

    save_data(data)

    await update.message.reply_text(
        "✅ Link permission granted"
    )

async def ban(update, context):

    admin = await is_admin(
        update.effective_chat,
        update.effective_user.id,
        context
    )

    if not admin:
        return

    if not update.message.reply_to_message:
        return

    target = update.message.reply_to_message.from_user

    await context.bot.ban_chat_member(
        update.effective_chat.id,
        target.id
    )

    await update.message.reply_text(
        "🚫 User banned"
    )

async def unban(update, context):

    admin = await is_admin(
        update.effective_chat,
        update.effective_user.id,
        context
    )

    if not admin:
        return

    if len(context.args) == 0:

        await update.message.reply_text(
            "/unban USER_ID"
        )

        return

    user_id = int(context.args[0])

    await context.bot.unban_chat_member(
        update.effective_chat.id,
        user_id
    )

    await update.message.reply_text(
        "✅ User unbanned"
    )

# =========================
# JOIN REQUEST
# =========================

async def approve_request(update, context):

    request = update.chat_join_request

    try:

        await context.bot.approve_chat_join_request(
            request.chat.id,
            request.from_user.id
        )

        group_name = request.chat.title

        member_count = await context.bot.get_chat_member_count(
            request.chat.id
        )

        image_path = create_welcome_image(
            request.from_user.first_name,
            group_name,
            member_count
        )

        with open(image_path, "rb") as photo:

            await context.bot.send_photo(
                chat_id=request.chat.id,
                photo=photo,
                caption=(
                    f"🎉 Welcome "
                    f"{request.from_user.first_name}!"
                )
            )

    except Exception as e:
        print(e)

# =========================
# MAIN
# =========================

def main():

    keep_alive()

    bot = Application.builder().token(
        BOT_TOKEN
    ).build()

    # Commands
    bot.add_handler(CommandHandler(
        "rules",
        rules
    ))

    bot.add_handler(CommandHandler(
        "stats",
        stats
    ))

    bot.add_handler(CommandHandler(
        "warn",
        warn
    ))

    bot.add_handler(CommandHandler(
        "unwarn",
        unwarn
    ))

    bot.add_handler(CommandHandler(
        "allowlink",
        allowlink
    ))

    bot.add_handler(CommandHandler(
        "ban",
        ban
    ))

    bot.add_handler(CommandHandler(
        "unban",
        unban
    ))

    # Messages
    bot.add_handler(
        MessageHandler(
            filters.TEXT |
            filters.CaptionRegex(".*"),
            handle_message
        )
    )

    # Join Request
    bot.add_handler(
        ChatJoinRequestHandler(
            approve_request
        )
    )

    print("Bot Running...")

    bot.run_polling()

if __name__ == "__main__":
    main()
