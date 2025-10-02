import telebot
import requests
import os
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Initialize Flask app
app = Flask(__name__)

# Define a simple route for health check
@app.route('/')
def home():
    return "Bot is running!"

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Get token from environment variable
LIKE_API_URL = "https://api-likes-alli-ff.vercel.app/like?uid=760840390"
GROUP_ID = -1002931591443  # Group ID
GROUP_LINK = "https://t.me/rsallanime"  # Group invite link

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Function to create inline keyboard with group link
def get_group_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Join Our Group", url=GROUP_LINK))
    return keyboard

# Function to check if message is in allowed group
def is_in_group(message):
    chat_id = message.chat.id
    return chat_id == GROUP_ID

# Start command (accessible in group only)
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not is_in_group(message):
        bot.reply_to(message, "⚠️ This bot can only be used in the designated group.")
        return
    
    bot.reply_to(message,
                 "👋 Welcome!\n\n"
                 "Send likes with:\n"
                 "<code>/like <region> <uid></code>\n\n"
                 "Example:\n"
                 "<code>/like bd 123456789</code>\n\n"
                 "Stay updated in our group:",
                 reply_markup=get_group_button(),
                 parse_mode="HTML")

# Help command (accessible in group only)
@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not is_in_group(message):
        bot.reply_to(message, "⚠️ This bot can only be used in the designated group.")
        return
    
    bot.reply_to(message,
                 "📖 <b>LikeBot Help</b>\n\n"
                 "Use command:\n"
                 "<code>/like <region> <uid></code>\n\n"
                 "Example:\n"
                 "<code>/like bd 123456789</code>\n\n"
                 "Supported regions: bd, in, pk, id, th, sg, eu, etc.",
                 parse_mode="HTML")

# Like command (accessible in group only)
@bot.message_handler(commands=['like'])
def like_cmd(message):
    if not is_in_group(message):
        bot.reply_to(message, "⚠️ This bot can only be used in the designated group.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message,
                     "⚠️ Wrong usage!\n\n"
                     "Correct format:\n"
                     "<code>/like <region> <uid></code>",
                     parse_mode="HTML")
        return

    region = args[1].lower()
    uid = args[2]

    try:
        resp = requests.get(f"{LIKE_API_URL}?server_name={region}&uid={uid}", timeout=15)
        if resp.status_code != 200:
            bot.send_message(message.chat.id, "🚨 API not responding, please try later.")
            return
        data = resp.json()
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Connection Error: {e}")
        return

    status = data.get("status", 0)

    if status == 1:
        likes_given = int(data.get("LikesGivenByAPI", 0) or 0)
        likes_before = int(data.get("LikesbeforeCommand", 0) or 0)
        likes_after = int(data.get("LikesafterCommand", 0) or 0)

        text = (
            "✅ <b>LIKE SUCCESS</b>\n\n"
            "👤 <b>Player:</b> {name}\n"
            "🆔 <b>UID:</b> {uid}\n"
            "🌍 <b>Region:</b> {region}\n\n"
            "📊 <b>Like Report</b>\n"
            "• Before: {before}\n"
            "• Sent: {sent}\n"
            "• Now: {after}\n\n"
            "🎯 Keep supporting!"
        ).format(
            name=data.get("PlayerNickname", "Unknown"),
            uid=data.get("UID", uid),
            region=region.upper(),
            before=likes_before,
            sent=likes_given,
            after=likes_after
        )

        bot.send_message(message.chat.id, text, parse_mode="HTML")

    elif status == 2:
        text = (
            "ℹ️ <b>Already Liked</b>\n\n"
            "👤 <b>Player:</b> {name}\n"
            "🆔 <b>UID:</b> {uid}\n"
            "🌍 <b>Region:</b> {region}\n\n"
            "💖 Current Likes: {likes}\n\n"
            "⚡ This account was already liked earlier."
        ).format(
            name=data.get("PlayerNickname", "Unknown"),
            uid=data.get("UID", uid),
            region=region.upper(),
            likes=data.get("LikesafterCommand", "?")
        )

        bot.send_message(message.chat.id, text, parse_mode="HTML")

    else:
        text = (
            "❌ <b>Like Failed</b>\n\n"
            "🆔 UID: {uid}\n"
            "🌍 Region: {region}\n\n"
            "Please check your details and try again."
        ).format(uid=uid, region=region.upper())

        bot.send_message(message.chat.id, text, parse_mode="HTML")

# Function to run the bot
def run_bot():
    bot.polling(none_stop=True)

# Start Flask and Bot in separate threads
if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # Start Flask server
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT env variable
    app.run(host="0.0.0.0", port=port)
