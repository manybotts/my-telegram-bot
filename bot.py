import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.ext import CallbackContext
from telegram.utils.helpers import escape_markdown
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

# Load MongoDB URI and Telegram Bot Token from environment variables
MONGO_URI = os.getenv('MONGO_URI')
BOT_API_TOKEN = os.getenv('BOT_API_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS').split(',')
FORCE_SUB_CHANNEL_1_ID = os.getenv('FORCE_SUB_CHANNEL_1_ID')
FORCE_SUB_CHANNEL_2_ID = os.getenv('FORCE_SUB_CHANNEL_2_ID')
DUMP_CHANNEL_ID = os.getenv('DUMP_CHANNEL_ID')

# Setup MongoDB connection
client = MongoClient(MONGO_URI)
db = client.get_database()
users_collection = db.users

# Initialize the bot
bot = Bot(BOT_API_TOKEN)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def is_admin(user_id):
    """Check if the user is an admin."""
    return str(user_id) in ADMIN_IDS

def store_user_info(user_id, username):
    """Store user info in MongoDB."""
    if users_collection.find_one({"user_id": user_id}) is None:
        users_collection.insert_one({"user_id": user_id, "username": username})

def start(update: Update, context: CallbackContext):
    """Command to start the bot and welcome the user."""
    user_id = update.message.from_user.id
    store_user_info(user_id, update.message.from_user.username)
    update.message.reply_text("Hello! I am a file management bot. Only admins can upload and generate links.")

def handle_files(update: Update, context: CallbackContext):
    """Handle file uploads from admins."""
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        update.message.reply_text("You are not authorized to upload files.")
        return

    if update.message.document:
        # Handle single file upload
        file = update.message.document
        file_id = file.file_id
        file_name = file.file_name

        # Upload the file to the dump channel
        file_link = bot.get_file(file_id).file_url
        bot.send_message(chat_id=DUMP_CHANNEL_ID, text=f"File uploaded: {file_name}\nLink: {file_link}")
        update.message.reply_text(f"File uploaded successfully!\nHere is the link: {file_link}")

    elif update.message.photo:
        # Handle photo upload
        photo = update.message.photo[-1]
        file_id = photo.file_id
        file_name = "photo.jpg"
        file_link = bot.get_file(file_id).file_url
        bot.send_message(chat_id=DUMP_CHANNEL_ID, text=f"Photo uploaded: {file_name}\nLink: {file_link}")
        update.message.reply_text(f"Photo uploaded successfully!\nHere is the link: {file_link}")
    else:
        update.message.reply_text("Please send a file or photo to upload.")

def handle_batch_files(update: Update, context: CallbackContext):
    """Handle batch file uploads."""
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        update.message.reply_text("You are not authorized to upload files.")
        return

    # Check for multiple documents (batch upload)
    if update.message.document:
        batch_files = []
        for doc in update.message.document:
            file_id = doc.file_id
            file_name = doc.file_name
            file_link = bot.get_file(file_id).file_url
            batch_files.append(f"{file_name}: {file_link}")

        # Upload the files to the dump channel as a batch
        bot.send_message(chat_id=DUMP_CHANNEL_ID, text=f"Batch files uploaded: \n\n" + "\n".join(batch_files))
        update.message.reply_text("Batch files uploaded successfully!\nHere are the links: \n" + "\n".join(batch_files))

def broadcast_message(update: Update, context: CallbackContext):
    """Send broadcast messages to all users."""
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        update.message.reply_text("You are not authorized to broadcast messages.")
        return

    # Get the message to broadcast
    broadcast_text = ' '.join(context.args)
    for user in users_collection.find():
        bot.send_message(chat_id=user["user_id"], text=broadcast_text)

    update.message.reply_text("Message broadcasted to all users.")

def check_subscription(user_id, context, force_channel_ids):
    """Check if user is subscribed to the required force sub channels."""
    for channel_id in force_channel_ids:
        if not bot.get_chat_member(channel_id, user_id).status in ['member', 'administrator']:
            return False
    return True

def retrieve_file(update: Update, context: CallbackContext):
    """Retrieve file based on the generated link."""
    query = update.callback_query
    user_id = query.from_user.id

    if not check_subscription(user_id, context, [FORCE_SUB_CHANNEL_1_ID, FORCE_SUB_CHANNEL_2_ID]):
        keyboard = [
            [
                InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{FORCE_SUB_CHANNEL_1_ID}"),
                InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{FORCE_SUB_CHANNEL_2_ID}")
            ],
            [InlineKeyboardButton("Try Again", callback_data="try_again")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            "You need to join both force subscription channels first to download files.",
            reply_markup=reply_markup
        )
        return

    # If user is subscribed, fetch file and send
    file_id = context.args[0]
    file = bot.get_file(file_id)
    file.download(f"{file_id}.pdf")  # Example download location

    with open(f"{file_id}.pdf", 'rb') as f:
        update.message.reply_document(f)

    query.message.reply_text(f"Here is your file {file_id}.")

def try_again(update: Update, context: CallbackContext):
    """User will try again after joining the channels."""
    update.message.reply_text("Please wait while we check your subscription status.")

def main():
    updater = Updater(BOT_API_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Command Handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.document | Filters.photo, handle_files))
    dispatcher.add_handler(CommandHandler('broadcast', broadcast_message))
    dispatcher.add_handler(CallbackQueryHandler(retrieve_file, pattern='^retrieve_'))
    dispatcher.add_handler(CallbackQueryHandler(try_again, pattern='^try_again$'))

    # Start polling
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
