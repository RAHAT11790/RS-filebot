import os
import re
import sqlite3
from flask import Flask
from pyrogram import Client, filters

# --- Flask server for Render ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running fine on Render!"

# --- Database setup ---
DB_FILE = "posts.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_name TEXT UNIQUE,
            link TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Bot setup ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL")  # e.g. "CARTOONFUNNY03"

bot = Client("anime-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Extract anime info ---
def extract_anime_info(text: str, buttons: list = None):
    anime_name, link = "", ""
    if text:
        match = re.search(r"[Tt][iɪ]tle['’`\-: ]*\s*(.+)", text)
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

def save_post_unique(anime_name: str, link: str):
    if not anime_name:
        return
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO posts (anime_name, link) VALUES (?, ?)", (anime_name, link))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already exists
    conn.close()

# --- Listen to channel messages ---
@bot.on_message(filters.chat(CHANNEL))
async def channel_listener(client, message):
    anime_name, link = extract_anime_info(
        message.text or message.caption,
        message.reply_markup.inline_keyboard if message.reply_markup else None
    )
    save_post_unique(anime_name, link)

# --- Command: /start ---
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    text = (
        "হ্যালো 👋\n\n"
        "আমি CartoonFunny03 চ্যানেলের অ্যানিমে কালেক্টর বট।\n"
        "আমার কাজ হলো চ্যানেলের পোস্ট থেকে অ্যানিমের নাম আর লিংক সংগ্রহ করে রাখা।\n\n"
        "📌 কমান্ড সমূহ:\n"
        "   • /start → বট সম্পর্কে তথ্য\n"
        "   • /list → সব অ্যানিমের নাম ও লিংক লিস্ট দেখাবে\n\n"
        "✅ আমাকে চ্যানেলে এডমিন করে রাখো, তাহলেই আমি অটোমেটিক সব নতুন অ্যানিমে যোগ করব।"
    )
    await message.reply_text(text)

# --- Command: /list ---
@bot.on_message(filters.command("list") & filters.private)
async def cmd_list(client, message):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT anime_name, link FROM posts ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.reply_text("কোনো অ্যানিমে পাওয়া যায়নি।")
        return

    text = "\n".join(
        f"• [{name}]({link})" if link else f"• {name}" for name, link in rows
    )
    await message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

# --- Run bot + Flask together ---
if __name__ == "__main__":
    import threading

    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)

    threading.Thread(target=run_flask).start()
    bot.run()
