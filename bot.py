import os
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import config

# Pyrogram Bot
bot = Client(
    "group_helper_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True
)

# Flask Server
server = Flask(__name__)

# ===========================
# Storage (Demo DB)
# ===========================
GROUP_WELCOME = {}
GROUP_WELCOME_PHOTO = {}
GROUP_LEAVE = {}
GROUP_RULES = {}
GROUP_FILTERS = {}
CLEAN_SERVICE = {}
BANNED_CONTENT = {}

# ===========================
# START Command
# ===========================
@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):
    me = await bot.get_me()
    buttons = [
        [InlineKeyboardButton("➕ Add me to your group", url=f"https://t.me/{me.username}?startgroup=true")]
    ]
    await message.reply_text(
        f"**🤖 {me.first_name} is Online!**\n\n"
        "📌 Available Commands:\n"
        "`/rs` - Add keyword filters\n"
        "`/setwelcome` - Set welcome message\n"
        "`/setwelcome_photo` - Set welcome photo\n"
        "`/setleave` - Set leave message\n"
        "`/rules` - Show rules\n"
        "`/setrules` - Set rules\n"
        "`/cleanservice all` - Auto clean join/leave messages\n"
        "`/ban` - Ban user/content\n\n"
        "⚠️ Only admins can use these commands.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ===========================
# Welcome / Leave
# ===========================
@bot.on_message(filters.new_chat_members)
async def welcome(client, message: Message):
    chat_id = message.chat.id
    if chat_id in GROUP_WELCOME:
        text = GROUP_WELCOME[chat_id].replace("{mention}", message.from_user.mention).replace("{group}", message.chat.title)
        if chat_id in GROUP_WELCOME_PHOTO:
            await message.reply_photo(GROUP_WELCOME_PHOTO[chat_id], caption=text)
        else:
            await message.reply_text(text)

@bot.on_message(filters.left_chat_member)
async def leave(client, message: Message):
    chat_id = message.chat.id
    if chat_id in GROUP_LEAVE:
        text = GROUP_LEAVE[chat_id].replace("{mention}", message.left_chat_member.mention).replace("{group}", message.chat.title)
        await message.reply_text(text)

@bot.on_message(filters.command("setwelcome") & filters.group)
async def set_welcome(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can set welcome message.")
    text = message.text.split(" ", 1)
    if len(text) < 2: return await message.reply_text("Usage: /setwelcome [text]")
    GROUP_WELCOME[message.chat.id] = text[1]
    await message.reply_text("✅ Welcome message updated!")

@bot.on_message(filters.command("setwelcome_photo") & filters.reply & filters.group)
async def set_welcome_photo(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can set welcome photo.")
    if message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_id
        GROUP_WELCOME_PHOTO[message.chat.id] = file_id
        await message.reply_text("✅ Welcome photo updated!")

@bot.on_message(filters.command("setleave") & filters.group)
async def set_leave(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can set leave message.")
    text = message.text.split(" ", 1)
    if len(text) < 2: return await message.reply_text("Usage: /setleave [text]")
    GROUP_LEAVE[message.chat.id] = text[1]
    await message.reply_text("✅ Leave message updated!")

# ===========================
# Rules
# ===========================
@bot.on_message(filters.command("rules") & filters.group)
async def rules(client, message: Message):
    if message.chat.id in GROUP_RULES:
        await message.reply_text(f"📌 Rules:\n\n{GROUP_RULES[message.chat.id]}")
    else:
        await message.reply_text("❌ No rules set yet.")

@bot.on_message(filters.command("setrules") & filters.group)
async def set_rules(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can set rules.")
    text = message.text.split(" ", 1)
    if len(text) < 2: return await message.reply_text("Usage: /setrules [rules]")
    GROUP_RULES[message.chat.id] = text[1]
    await message.reply_text("✅ Rules updated!")

# ===========================
# Clean Service
# ===========================
@bot.on_message(filters.command("cleanservice") & filters.group)
async def clean_service(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can use this.")
    if len(message.command) > 1 and message.command[1] == "all":
        CLEAN_SERVICE[message.chat.id] = True
        await message.reply_text("✅ Join/Leave messages will be deleted after 5 minutes.")

@bot.on_message(filters.service, group=1)
async def service_cleaner(client, message: Message):
    if message.chat.id in CLEAN_SERVICE:
        await message.delete(delay=300)

# ===========================
# Filters (/rs)
# ===========================
@bot.on_message(filters.command("rs") & filters.group)
async def add_filter(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can set filters.")
    args = message.text.split(" ", 2)
    if len(args) < 3: return await message.reply_text("Usage: /rs [keyword] [reply text]")
    keyword, reply = args[1], args[2]
    if message.chat.id not in GROUP_FILTERS:
        GROUP_FILTERS[message.chat.id] = {}
    GROUP_FILTERS[message.chat.id][keyword.lower()] = reply
    await message.reply_text(f"✅ Filter added:\n**{keyword}** → {reply}")

@bot.on_message(filters.text & filters.group, group=2)
async def filter_check(client, message: Message):
    chat_id = message.chat.id
    if chat_id in GROUP_FILTERS:
        for keyword, reply in GROUP_FILTERS[chat_id].items():
            if keyword in message.text.lower():
                await message.reply_text(reply)
                break

# ===========================
# Ban System
# ===========================
@bot.on_message(filters.command("ban") & filters.group)
async def ban_command(client, message: Message):
    if not await is_admin(message): return await message.reply_text("⚠️ Only admins can ban.")
    if len(message.command) < 2: return await message.reply_text("Usage: /ban [link|photo|video|username|user_id]")
    target = message.command[1].lower()
    BANNED_CONTENT.setdefault(message.chat.id, set()).add(target)
    await message.reply_text(f"🚫 Banned: {target}")

@bot.on_message(filters.group, group=3)
async def auto_ban(client, message: Message):
    chat_id = message.chat.id
    if chat_id in BANNED_CONTENT:
        for banned in BANNED_CONTENT[chat_id]:
            if banned == "link" and message.entities:
                for ent in message.entities:
                    if ent.type in ["url", "text_link"]:
                        await message.delete()
                        await bot.kick_chat_member(chat_id, message.from_user.id)
            elif banned == "photo" and message.photo:
                await message.delete()
                await bot.kick_chat_member(chat_id, message.from_user.id)
            elif banned == "video" and message.video:
                await message.delete()
                await bot.kick_chat_member(chat_id, message.from_user.id)
            elif banned.startswith("@") and message.from_user.username == banned.strip("@"):
                await message.delete()
                await bot.kick_chat_member(chat_id, message.from_user.id)
            elif banned.isdigit() and str(message.from_user.id) == banned:
                await message.delete()
                await bot.kick_chat_member(chat_id, message.from_user.id)

# ===========================
# Utility: Check Admin
# ===========================
async def is_admin(message: Message):
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ["administrator", "creator"]

# ===========================
# Flask Webhook
# ===========================
@server.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    bot.process_update(update)
    return "OK", 200

# ===========================
# Main
# ===========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    bot.start()
    bot.set_webhook(config.WEBHOOK_URL)
    server.run(host="0.0.0.0", port=port)
