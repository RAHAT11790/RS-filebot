import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import uuid  # ইউনিক ID জেনারেটের জন্য

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ডাটা স্টোরেজ (প্রোডাকশনে ডাটাবেস ব্যবহার করো)
batch_data = {}  # key: batch_id, value: list of file_ids

# তোমার চ্যানেল ID (যেমন -1001234567890) - এটি এডিট করা হয়েছে
CHANNEL_ID = -1002715710203  # কনটেন্ট চ্যানেলের ID

# রিকোয়ার্ড চ্যানেলগুলোর লিস্ট (ID হিসেবে) - ডাইনামিক, শুরুতে খালি
REQUIRED_CHANNELS = []  # রানটাইমে অ্যাড হবে

# অ্যাডমিন ID - এটি এডিট করা হয়েছে
ADMIN_ID = 6621572366  # তোমার ID

# চেক ফাংশন: ইউজার সব চ্যানেলে জয়েন করেছে কি না
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if not REQUIRED_CHANNELS:
        return True  # কোনো চ্যানেল না থাকলে অ্যালাউ
    for channel_id in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logger.error(f"Error checking membership for {channel_id}: {e}")
            return False
    return True

# জয়েন লিংক জেনারেট করার ফাংশন
def get_join_links():
    links = [f"https://t.me/c/{str(channel_id).replace('-100', '')}/1" for channel_id in REQUIRED_CHANNELS]
    return "\n".join(links)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        await update.message.reply_text(
            "তুমি সব রিকোয়ার্ড চ্যানেলে জয়েন করোনি। জয়েন করো:\n" + get_join_links() + "\nতারপর /start দাও।"
        )
        return
    
    # কাস্টমাইজেবল মেনু - এখানে টেক্সট এবং বাটন এডিট করো
    keyboard = [
        [InlineKeyboardButton("Japanese", callback_data='japanese')],
        [InlineKeyboardButton("Western", callback_data='western')],
        [InlineKeyboardButton("Doujin", callback_data='doujin')],
        [InlineKeyboardButton("Anime Parody", callback_data='anime_parody')],
        [InlineKeyboardButton("Adult Manhwa", callback_data='adult_manhwa')],
        [InlineKeyboardButton("Indian Work", callback_data='indian_work')],
        [InlineKeyboardButton("Chinese Work", callback_data='chinese_work')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "হ্যালো! আমি তোমার অ্যানিমে বট। নিচের ক্যাটাগরি থেকে চয়েস করো।\n"
        "কমান্ডস (অ্যাডমিন অনলি):\n"
        "/forcesub - ফোর্স সাব চ্যানেল অ্যাড করো\n"
        "/batch - মাল্টিপল ফাইলের লিংক তৈরি\n"
        "/users - টোটাল ইউজার দেখো\n"
        "/broadcast - সবাইকে মেসেজ পাঠাও",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        await update.callback_query.answer("জয়েন করো প্রথমে!")
        return
    # ক্যাটাগরি বাটন হ্যান্ডেল - এখানে কাস্টমাইজ করো
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"তুমি চয়েস করেছো: {query.data}. এখানে কনটেন্ট যোগ করো।")

async def forcesub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারে।")
        return
    context.user_data['forcesub_mode'] = True
    await update.message.reply_text("যে চ্যানেল অ্যাড করতে চাও, সেখান থেকে একটা মেসেজ ফরওয়ার্ড করো।")

# ফোর্স সাব হ্যান্ডলার: ফরওয়ার্ড মেসেজ থেকে চ্যানেল অ্যাড
async def handle_forcesub_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    if 'forcesub_mode' not in context.user_data or not context.user_data['forcesub_mode']:
        return
    message = update.message
    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        if channel_id not in REQUIRED_CHANNELS:
            REQUIRED_CHANNELS.append(channel_id)
            await message.reply_text(f"চ্যানেল {channel_id} অ্যাড করা হয়েছে। কারেন্ট লিস্ট: {REQUIRED_CHANNELS}")
        else:
            await message.reply_text(f"চ্যানেল {channel_id} ইতিমধ্যে অ্যাড করা।")
        del context.user_data['forcesub_mode']
    else:
        await message.reply_text("এটি ফরওয়ার্ড মেসেজ নয়।")

async def batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারে।")
        return
    if not await is_user_joined(update, context):
        await update.message.reply_text(
            "তুমি সব রিকোয়ার্ড চ্যানেলে জয়েন করোনি। জয়েন করো:\n" + get_join_links() + "\nতারপর আবার চেষ্টা করো।"
        )
        return
    await update.message.reply_text("চ্যানেল থেকে প্রথম মেসেজ ফরওয়ার্ড করো, তারপর শেষ মেসেজ ফরওয়ার্ড করো।")

# মেসেজ হ্যান্ডলার: ফরওয়ার্ড মেসেজ চেক করো (batch-এর জন্য)
async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID and 'forcesub_mode' not in context.user_data:
        return
    if not await is_user_joined(update, context):
        await update.message.reply_text(
            "তুমি সব রিকোয়ার্ড চ্যানেলে জয়েন করোনি। জয়েন করো:\n" + get_join_links() + "\nতারপর আবার চেষ্টা করো।"
        )
        return
    message = update.message
    if message.forward_from_chat and message.forward_from_chat.id == CHANNEL_ID:
        if 'first_msg_id' not in context.user_data:
            context.user_data['first_msg_id'] = message.forward_from_message_id
            await message.reply_text("প্রথম মেসেজ রিসিভড। এখন শেষ মেসেজ ফরওয়ার্ড করো।")
        elif 'last_msg_id' not in context.user_data:
            context.user_data['last_msg_id'] = message.forward_from_message_id
            await message.reply_text("শেষ মেসেজ রিসিভড। লিংক তৈরি করছি...")
            
            # মধ্যবর্তী মেসেজ কালেক্ট করো
            first_id = context.user_data['first_msg_id']
            last_id = context.user_data['last_msg_id']
            file_ids = []
            
            # চ্যানেল থেকে মেসেজ লুপ করে কালেক্ট (বট অ্যাডমিন হলে কাজ করবে)
            current_id = first_id
            while current_id <= last_id:
                try:
                    msg = await context.bot.get_message(chat_id=CHANNEL_ID, message_id=current_id)
                    if msg.document or msg.video or msg.photo:
                        file_id = msg.document.file_id if msg.document else (msg.video.file_id if msg.video else msg.photo[-1].file_id)
                        file_ids.append(file_id)
                except Exception as e:
                    logger.error(f"Error getting message {current_id}: {e}")
                current_id += 1
            
            if file_ids:
                batch_id = str(uuid.uuid4())[:8]  # ইউনিক ID
                batch_data[batch_id] = file_ids
                bot_username = (await context.bot.get_me()).username
                link = f"https://t.me/{bot_username}?start={batch_id}"
                await message.reply_text(f"ব্যাচ লিংক তৈরি: {link}")
            else:
                await message.reply_text("কোনো ফাইল পাওয়া যায়নি।")
            
            # রিসেট
            if 'first_msg_id' in context.user_data:
                del context.user_data['first_msg_id']
            if 'last_msg_id' in context.user_data:
                del context.user_data['last_msg_id']
        else:
            await message.reply_text("অন্য চ্যানেল থেকে ফরওয়ার্ড করো না।")
    # forcesub-এর জন্য চেক
    elif 'forcesub_mode' in context.user_data and context.user_data['forcesub_mode']:
        await handle_forcesub_forward(update, context)

# লিংক থেকে ফাইল পাঠানো
async def handle_start_with_param(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        await update.message.reply_text(
            "তুমি সব রিকোয়ার্ড চ্যানেলে জয়েন করোনি। জয়েন করো:\n" + get_join_links() + "\nতারপর আবার চেষ্টা করো।"
        )
        return
    if context.args:
        batch_id = context.args[0]
        if batch_id in batch_data:
            for file_id in batch_data[batch_id]:
                await update.message.reply_document(file_id)  # বা reply_video/photo যা লাগে
            await update.message.reply_text("সব ফাইল পাঠানো হয়েছে।")
        else:
            await update.message.reply_text("ইনভ্যালিড লিংক।")

# অন্য কমান্ডস (যেমন /users, /broadcast) - এগুলো শুধু অ্যাডমিনের জন্য
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারে।")
        return
    if not await is_user_joined(update, context):
        await update.message.reply_text(
            "তুমি সব রিকোয়ার্ড চ্যানেলে জয়েন করোনি। জয়েন করো:\n" + get_join_links() + "\nতারপর আবার চেষ্টা করো।"
        )
        return
    await update.message.reply_text("টোটাল ইউজার: 0 (কাস্টমাইজ করো)")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারে।")
        return
    if not await is_user_joined(update, context):
        await update.message.reply_text(
            "তুমি সব রিকোয়ার্ড চ্যানেলে জয়েন করোনি। জয়েন করো:\n" + get_join_links() + "\nতারপর আবার চেষ্টা করো।"
        )
        return
    await update.message.reply_text("ব্রডকাস্ট সেন্ড করা হয়েছে (কাস্টমাইজ করো)")

def main():
    # তোমার API Token - এটি এডিট করা হয়েছে
    TOKEN = '8257089548:AAG3hpoUToom6a71peYep-DBfgPiKU3wPGE'  # BotFather থেকে নেওয়া
    
    application = Application.builder().token(TOKEN).build()
    
    # হ্যান্ডলার যোগ
    application.add_handler(CommandHandler("start", handle_start_with_param if context.args else start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("batch", batch))
    application.add_handler(CommandHandler("nbatch", batch))  # একই ফাংশন
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("forcesub", forcesub))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_forwarded))  # ফরওয়ার্ড হ্যান্ডেল
    
    application.run_polling()

if __name__ == '__main__':
    main()
