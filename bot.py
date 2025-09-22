import os
import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, RPCError

# Logging সেটআপ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables থেকে কনফিগারেশন
API_ID = int(os.environ.get('API_ID', '25976192'))
API_HASH = os.environ.get('API_HASH', '8ba23141980539b4896e5adbc4ffd2e2')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8257089548:AAG3hpoUToom6a71peYep-DBfgPiKU3wPGE')

# গ্লোবাল ইউজারনেম স্টোর
RS_USERNAMES = [None, None, None]

# হেল্পার ফাংশন
def _normalize_username(u: str) -> str:
    if not u:
        return None
    u = u.strip()
    if u.startswith("@"):
        u = u[1:]
    u = re.sub(r"^https?://(?:www\.)?t\.me/", "", u, flags=re.IGNORECASE)
    u = re.sub(r"^t\.me/", "", u, flags=re.IGNORECASE)
    return u

def replace_all_usernames(text: str, new_usernames: list) -> str:
    if not text or not new_usernames or all(u is None for u in new_usernames):
        return text
    pattern = r'@[a-zA-Z0-9_]{1,32}|t\.me/[a-zA-Z0-9_]{1,32}|https?://(?:www\.)?t\.me/[a-zA-Z0-9_]{1,32}'
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    if not matches:
        return text
    result = []
    last_idx = 0
    for i, m in enumerate(matches):
        start, end = m.span()
        orig = m.group(0)
        result.append(text[last_idx:start])
        if i < len(new_usernames) and new_usernames[i]:
            newu = new_usernames[i]
            if orig.startswith("@"):
                replacement = f"@{newu}"
            elif orig.lower().startswith("t.me/"):
                replacement = f"t.me/{newu}"
            else:
                replacement = f"https://t.me/{newu}"
            result.append(replacement)
        else:
            result.append(orig)
        last_idx = end
    result.append(text[last_idx:])
    return "".join(result)

# Pyrogram বট
app = Client("rs_updater_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        """🤖 Welcome to HINDI ANIME CHANNEL BOT

        ✅ How to use:
        1. First set your usernames: /set_rs username1 username2 username3
        2. Then COPY-PASTE (not forward) any message here
        3. For batch update in channel: /batch_update @channelusername 50 (last 50 messages)

        ❌ DON'T FORWARD MESSAGES
        ✅ COPY-PASTE INSTEAD"""
    )

@app.on_message(filters.command("set_rs") & filters.private)
async def set_rs(client, message):
    global RS_USERNAMES
    args = message.text.split()[1:]
    if not args or len(args) > 3:
        await message.reply_text("Usage: /set_rs username1 username2 username3 (up to 3)")
        return
    normalized = [_normalize_username(u) for u in args[:3]]
    normalized += [None] * (3 - len(normalized))
    RS_USERNAMES = normalized
    await message.reply_text(f"✅ RS set: @{RS_USERNAMES[0]} | @{RS_USERNAMES[1]} | @{RS_USERNAMES[2]}")

@app.on_message(filters.command("batch_update") & filters.private)
async def batch_update(client, message):
    global RS_USERNAMES
    if not RS_USERNAMES[0]:
        await message.reply_text("❌ Please set RS usernames first with /set_rs")
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("Usage: /batch_update @channelusername message_count (e.g., /batch_update @chan 50)")
        return
    channel = parts[1].lstrip("@")
    try:
        total_count = int(parts[2])
    except ValueError:
        await message.reply_text("❌ message_count must be a number.")
        return
    if total_count > 5000:
        await message.reply_text("❌ Too many messages at once. Try <= 5000.")
        return
    await message.reply_text(f"🔄 Starting: scanning last {total_count} messages in @{channel}...")
    try:
        me = await client.get_me()
        member = await client.get_chat_member(channel, me.id)
        if member.status not in ("administrator", "creator") or not member.privileges.can_edit_messages:
            await message.reply_text("❌ Bot must be admin with edit rights.")
            return
        processed = 0
        edited = 0
        async for msg in client.get_chat_history(channel, limit=total_count):
            processed += 1
            old_text = msg.text or msg.caption or ""
            if not old_text or not old_text.strip():
                continue
            new_text = replace_all_usernames(old_text, RS_USERNAMES)
            if new_text != old_text:
                try:
                    if msg.text:
                        await client.edit_message_text(chat_id=channel, message_id=msg.message_id, text=new_text)
                    elif msg.caption:
                        await client.edit_message_caption(chat_id=channel, message_id=msg.message_id, caption=new_text)
                    edited += 1
                except FloodWait as fw:
                    await asyncio.sleep(fw.x + 1)
                except RPCError as e:
                    logger.error(f"Edit error: {e}")
            await asyncio.sleep(0.5)  # দ্রুত কাজের জন্য কম ডিলে
            if processed % 50 == 0:
                await message.reply_text(f"Progress: {processed}/{total_count}, edited {edited}")
        await message.reply_text(f"✅ Done. Processed: {processed}, Edited: {edited}")
    except Exception as e:
        logger.exception("Batch update failed")
        await message.reply_text(f"❌ Failed: {e}")

@app.on_message(filters.text & filters.private)
async def process_message(client, message):
    if message.forward_date:
        await message.reply_text("❌ Don't forward, COPY-PASTE instead! Use /start")
        return
    text = message.text or message.caption or ""
    if not RS_USERNAMES[0] or not text.strip():
        return
    new_text = replace_all_usernames(text, RS_USERNAMES)
    if new_text != text:
        await message.reply_text(new_text)

if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
