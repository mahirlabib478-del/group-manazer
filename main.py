from flask import Flask, request
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import os

app = Flask(__name__)

# তোমার টোকেন এখানে বসাও
TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
bot = Bot(TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# গালি এবং কিওয়ার্ডের তালিকা
BAD_WORDS =["gali1", "gali2", "bal", "chuda"] # এখানে তোমার বাংলা/বাংলিশ গালি যোগ করো
EPISODE_KEYWORDS =["আজকের এপিসোড", "এপিসোড দেন", "কখন দিবেন", "ep debo"]

# ওয়ার্নিং ট্র্যাক করার ডিকশনারি
warnings = {}

def is_admin(update):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    member = bot.get_chat_member(chat_id, user_id)
    return member.status in ['administrator', 'creator']

def handle_message(update, context):
    if not update.message or is_admin(update):
        return

    text = update.message.text.lower()
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    # ১. লিংক ডিটেকশন
    if "http" in text or "t.me" in text:
        update.message.delete()
        update.message.reply_text(f"দুঃখিত @{update.message.from_user.username}, গ্রুপে লিংক দেয়া নিষেধ!")
        return

    # ২. গালি ডিটেকশন
    if any(word in text for word in BAD_WORDS):
        warnings[user_id] = warnings.get(user_id, 0) + 1
        if warnings[user_id] >= 3:
            bot.ban_chat_member(chat_id, user_id)
            update.message.reply_text("৩ বার সতর্ক করার পরেও গালি দেয়ায় আপনাকে ব্যান করা হলো।")
        else:
            update.message.reply_text(f"সতর্কতা ({warnings[user_id]}/3): গালি দেয়া থেকে বিরত থাকুন!")
        return

    # ৩. এপিসোড রিকোয়েস্ট
    if any(key in text for key in EPISODE_KEYWORDS):
        update.message.reply_text("ধৈর্য ধরুন! এপিসোড কাজ চলছে, শীঘ্রই দেওয়া হবে।")

# রাউটিং
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
