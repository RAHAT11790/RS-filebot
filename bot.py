import asyncio
from telethon import TelegramClient, events
from fastapi import FastAPI
import os
import uvicorn

# =========================
# Environment variables
# =========================
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")
port = int(os.environ.get("PORT", 8000))  # Render এর PORT

# =========================
# Telegram bot setup
# =========================
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

messages = []
reply_count = 0

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    help_text = """হ্যালো! আমি বট। আমি করতে পারি:
1. /message_list – একসাথে অনেক মেসেজ সেট করতে পারো
2. /reply_set <number> – কতগুলো মেসেজ পাঠাবে সেট করতে পারো
3. /reply – নির্ধারিত সংখ্যক মেসেজ ৫ সেকেন্ড অন্তর পাঠাবে
"""
    await event.respond(help_text)

@client.on(events.NewMessage(pattern='/message_list'))
async def message_list(event):
    await event.respond("মেসেজগুলো পাঠাও, প্রতিটি মেসেজ নতুন লাইনে। শেষ হলে /done লিখো।")
    msgs = []
    while True:
        response = await client.wait_for(events.NewMessage(from_users=event.sender_id))
        text = response.raw_text
        if text == "/done":
            break
        msgs.append(text)
        await response.respond("মেসেজ যোগ করা হয়েছে।")
    
    global messages
    messages = msgs
    await client.send_message(event.chat_id, f"{len(messages)} মেসেজ সংরক্ষিত হয়েছে!")

@client.on(events.NewMessage(pattern='/reply_set (\d+)'))
async def set_reply(event):
    global reply_count
    reply_count = int(event.pattern_match.group(1))
    await event.respond(f"মেসেজ রিপ্লাই সংখ্যা সেট করা হয়েছে: {reply_count}")

@client.on(events.NewMessage(pattern='/reply'))
async def reply_messages(event):
    if not messages:
        await event.respond("মেসেজ লিস্ট খালি। /message_list দিয়ে প্রথমে মেসেজ যোগ করুন।")
        return
    if reply_count == 0:
        await event.respond("মেসেজ রিপ্লাই সংখ্যা সেট করা হয়নি। /reply_set <number> ব্যবহার করুন।")
        return
    
    await event.respond(f"{reply_count} মেসেজ পাঠানো শুরু হচ্ছে...")
    
    for i in range(min(reply_count, len(messages))):
        await client.send_message(event.chat_id, messages[i])
        await asyncio.sleep(5)
    
    await event.respond("মেসেজ পাঠানো শেষ হয়েছে।")

# =========================
# FastAPI web server (Render PORT keepalive)
# =========================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running!"}

# =========================
# Run both Telegram bot and web server
# =========================
async def main():
    await client.start()
    print("Telegram Bot is running...")

    # Run FastAPI server concurrently
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

asyncio.run(main())
