import os
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Dispatcher

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))  # চ্যানেল ID
PORT = int(os.environ.get("PORT", 8000))

# ------------------------
# Global Variables
# ------------------------
KEYWORDS_DB = {}          # চ্যানেল থেকে আসা কিওয়ার্ড
KEYWORD_ACTIVE = True     # /stop_all_key এর জন্য
WELCOME_MESSAGE = "স্বাগতম!"
CLEAN_SERVICE = True
BLOCKS = {"photo": True, "video": True, "link": True, "forward": True}

bot = Bot(BOT_TOKEN)
app = FastAPI()
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# ------------------------
# Admin Check
# ------------------------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ["administrator", "creator"]

# ------------------------
# /stop_all_key Command
# ------------------------
async def stop_all_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global KEYWORD_ACTIVE
    if not await is_admin(update, context):
        await update.message.reply_text("শুধুমাত্র অ্যাডমিন ব্যবহার করতে পারবে।")
        return
    KEYWORD_ACTIVE = False
    await update.message.reply_text("কিওয়ার্ড সিস্টেম বন্ধ করা হলো। সব কিওয়ার্ড অক্ষুণ্ণ থাকবে।")

# ------------------------
# Welcome / Leave
# ------------------------
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        msg = await update.message.reply_text(f"{member.full_name}, {WELCOME_MESSAGE}")
        if CLEAN_SERVICE:
            await msg.delete(delay=5)

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if CLEAN_SERVICE:
        await update.message.delete(delay=5)

# ------------------------
# Channel Post Handler
# ------------------------
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global KEYWORD_ACTIVE
    if not KEYWORD_ACTIVE:
        return
    msg = update.message
    if msg.forward_from_chat and msg.forward_from_chat.id == CHANNEL_ID:
        text = msg.text or msg.caption
        if text:
            KEYWORDS_DB[text.lower()] = text
            print(f"New keyword saved: {text}")

# ------------------------
# Check Keywords in Group
# ------------------------
async def check_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not KEYWORD_ACTIVE:
        return
    text = update.message.text.lower()
    for keyword, reply in KEYWORDS_DB.items():
        if keyword in text:
            await update.message.reply_text(reply)

# ------------------------
# Block Messages
# ------------------------
async def block_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.photo and BLOCKS.get("photo"):
        await msg.delete()
    if msg.video and BLOCKS.get("video"):
        await msg.delete()
    if msg.forward_from_chat and BLOCKS.get("forward"):
        await msg.delete()
    if msg.entities and any(e.type == "url" for e in msg.entities) and BLOCKS.get("link"):
        await msg.delete()

# ------------------------
# /help Command
# ------------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("শুধুমাত্র অ্যাডমিন ব্যবহার করতে পারবে।")
        return
    await update.message.reply_text("অ্যাডমিন কমান্ড: /stop_all_key, /help")

# ------------------------
# Dispatcher Handlers
# ------------------------
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("stop_all_key", stop_all_key))
dispatcher.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
dispatcher.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, leave))
dispatcher.add_handler(MessageHandler(filters.ALL, channel_post_handler))
dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), check_keywords))
dispatcher.add_handler(MessageHandler(filters.ALL, block_messages))

# ------------------------
# Telegram Webhook
# ------------------------
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await dispatcher.process_update(update)
    return {"status": "ok"}
