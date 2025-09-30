from dotenv import load_dotenv
import os
import re
import sqlite3
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# --- Load environment variables from .env file ---
load_dotenv()

# --- Flask server for Render ---
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running fine on Render!"

# --- Database setup ---
DB_FILE = "posts.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)  # টাইমআউট যোগ
    cur = conn.cursor()
    # posts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_name TEXT,
            link TEXT,
            UNIQUE(anime_name, link)
        )
    """)
    # history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            anime_name TEXT PRIMARY KEY,
            link TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Bot setup ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL")  # e.g. "@CARTOONFUNNY03"

bot = Client("anime-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Utility functions ---
def save_post_unique(anime_name: str, link: str):
    if not anime_name:
        return
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO posts (anime_name, link) VALUES (?, ?)", (anime_name, link))
        conn.commit()
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("Database locked, retrying...")
            import time
            time.sleep(5)
            cur.execute("INSERT OR IGNORE INTO posts (anime_name, link) VALUES (?, ?)", (anime_name, link))
            conn.commit()
        else:
            raise e
    except:
        pass
    conn.close()

def save_history(anime_name: str, link: str):
    if not anime_name:
        return
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO history (anime_name, link) VALUES (?, ?)", (anime_name, link))
        conn.commit()
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("Database locked, retrying...")
            import time
            time.sleep(5)
            cur.execute("INSERT OR IGNORE INTO history (anime_name, link) VALUES (?, ?)", (anime_name, link))
            conn.commit()
        else:
            raise e
    except:
        pass
    conn.close()

def extract_anime_info(text: str, buttons=None):
    anime_name, link = "", ""
    if text:
        match = re.search(r"(.+)", text.splitlines()[0])
        if match:
            anime_name = match.group(1).strip()
    if buttons:
        for row in buttons:
            for btn in row:
                if hasattr(btn, "text") and "watch" in btn.text.lower():
                    if hasattr(btn, "url") and btn.url:
                        link = btn.url
                        break
    return anime_name, link

# --- Historical fetch with limit ---
async def fetch_history(limit=None):
    try:
        async with Client("anime-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, takeout=True) as app_client:
            offset = 0
            while True:
                async for msg in app_client.get_chat_history(CHANNEL, limit=limit or 200, offset=offset):
                    text = msg.text or msg.caption or ""
                    buttons = msg.reply_markup.inline_keyboard if msg.reply_markup else None
                    name, link = extract_anime_info(text, buttons)
                    save_post_unique(name, link)
                offset += limit or 200
                await asyncio.sleep(1)  # FloodWait এড়ানোর জন্য
                if not msg:  # আর মেসেজ নেই
                    break
            print("Historical fetch complete.")
    except FloodWait as e:
        print(f"FloodWait: Waiting {e.value} seconds...")
        await asyncio.sleep(e.value)
        await fetch_history(limit=limit)

# --- Listener for new posts ---
@bot.on_message(filters.chat(CHANNEL))
async def channel_listener(client, message):
    text = message.text or message.caption or ""
    buttons = message.reply_markup.inline_keyboard if message.reply_markup else None
    name, link = extract_anime_info(text, buttons)
    save_post_unique(name, link)

# --- /start command ---
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    text = (
        "হ্যালো 👋\n\n"
        "আমি চ্যানেলের অ্যানিমে কালেক্টর বট।\n\n"
        "📌 কমান্ড:\n"
        "   • /start → বট তথ্য\n"
        "   • /fetch <limit> → চ্যানেলের পুরোনো হিস্টোরি লোড করবে (যেমন: /fetch 50)\n"
        "   • /list <offset> → ৫০ টা করে অ্যানিমে নাম ও লিঙ্ক দেখাবে\n"
        "   • /list history → ইতিমধ্যেই দেখা নামগুলো দেখাবে\n\n"
        "উদাহরণ: /list 0 → প্রথম ৫০, /fetch 50 → ৫০-৫০ করে ফেচ"
    )
    await message.reply_text(text)

# --- /fetch command with limit ---
@bot.on_message(filters.command("fetch") & filters.private)
async def fetch_cmd(client, message):
    text_parts = message.text.split()
    limit = 200  # ডিফল্ট লিমিট
    if len(text_parts) > 1:
        try:
            limit = int(text_parts[1])  # /fetch 50 থেকে 50 নেবে
            if limit <= 0:
                await message.reply_text("লিমিট ০ বা কম হতে পারে না। ডিফল্ট ২০০ ব্যবহৃত হবে।")
                limit = 200
        except ValueError:
            await message.reply_text("লিমিট একটি সংখ্যা হতে হবে। ডিফল্ট ২০০ ব্যবহৃত হবে।")
            limit = 200

    await message.reply_text(f"হিস্টোরি ফেচ শুরু হচ্ছে... (লিমিট: {limit}, এতে সময় লাগতে পারে)")
    await fetch_history(limit=limit)
    await message.reply_text("হিস্টোরি ফেচ সম্পূর্ণ!")

# --- /list command ---
@bot.on_message(filters.command("list") & filters.private)
async def list_cmd(client, message):
    text_parts = message.text.split()
    if len(text_parts) > 1 and text_parts[1].lower() == "history":
        # Show history
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cur = conn.cursor()
        cur.execute("SELECT anime_name, link FROM history ORDER BY first_seen ASC")
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await message.reply_text("কোনো history পাওয়া যায়নি। /fetch চালান।")
            return
        text_lines = [f"• [{name}]({link})" if link else f"• {name}" for name, link in rows]
        await message.reply_text("\n".join(text_lines), parse_mode="Markdown", disable_web_page_preview=True)
        return

    # Normal list pagination
    try:
        offset = int(text_parts[1]) if len(text_parts) > 1 else 0
    except:
        offset = 0

    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cur.execute("SELECT anime_name, link FROM posts ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    # Filter duplicates: keep first link per anime_name
    seen = set()
    filtered = []
    for name, link in rows:
        if name not in seen:
            filtered.append((name, link))
            seen.add(name)
            save_history(name, link)  # save to history

    page = filtered[offset: offset + 50]
    if not page:
        await message.reply_text("আর কোনো অ্যানিমে নেই।")
        return

    text_lines = [f"• [{name}]({link})" if link else f"• {name}" for name, link in page]
    await message.reply_text("\n".join(text_lines), parse_mode="Markdown", disable_web_page_preview=True)

# --- Run Flask + Bot ---
if __name__ == "__main__":
    # NO historical fetch at startup to avoid flood
    # Start Flask in a thread
    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    threading.Thread(target=run_flask).start()

    # Run bot
    bot.run()
