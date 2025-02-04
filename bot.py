import os
import logging
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from pymongo import MongoClient
from flask import Flask, jsonify
from threading import Thread

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB Setup
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client['file_management']
files_collection = db['files']  # To store file metadata

# Telegram setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DUMP_CHANNEL_ID = os.getenv("DUMP_CHANNEL_ID")  # Private dump channel ID
SUB_CHANNEL_1 = os.getenv("SUB_CHANNEL_1")  # First force sub channel ID
SUB_CHANNEL_2 = os.getenv("SUB_CHANNEL_2")  # Second force sub channel ID
ADMINS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS").split(',')]
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME")  # Your bot's username without '@'

# Initialize Flask app
app = Flask(__name__)

def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    update.message.reply_text(
        f'Hello, {user.first_name}! Welcome to the file management bot. Use /help to see available commands.',
        reply_markup=ForceReply(selective=True),
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Available commands:\n/start - Start the bot\n/help - Show help\n/upload - Upload a file (admins only)")

def upload_file(update: Update, context: CallbackContext):
    if update.message.from_user.id in ADMINS:
        update.message.reply_text("Please send me the file(s) you'd like to upload.")
    else:
        update.message.reply_text("You are not authorized to upload files.")

def handle_document(update: Update, context: CallbackContext):
    if update.message.from_user.id in ADMINS:
        document = update.message.document
        new_file = context.bot.send_document(chat_id=DUMP_CHANNEL_ID, document=document)
        files_collection.insert_one({
            'file_name': document.file_name,
            'file_id': new_file.document.file_id,
            'user_id': update.message.from_user.id
        })
        
        update.message.reply_text("File(s) uploaded to the dump channel and stored.")
    else:
        update.message.reply_text("You are not authorized to upload files.")

def generate_link(file_id):
    return f"https://t.me/{TELEGRAM_USERNAME}/{file_id}"

def handle_retrieve_file(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    # Check if user is subscribed
    if not is_user_subscribed(context, user_id):
        send_subscription_buttons(context, update.message.chat_id)
        return

    file_name = context.args[0] if context.args else None  # Pass the file identifier as an argument
    file_data = files_collection.find_one({"file_name": file_name})

    if file_data:
        context.bot.send_document(chat_id=user_id, document=file_data['file_id'])
    else:
        update.message.reply_text("File not found!")

def is_user_subscribed(context, user_id):
    # Check subscription for both channels
    chat_member_1 = context.bot.get_chat_member(SUB_CHANNEL_1, user_id)
    chat_member_2 = context.bot.get_chat_member(SUB_CHANNEL_2, user_id)
    return chat_member_1.status in ["member", "administrator"] and chat_member_2.status in ["member", "administrator"]

def send_subscription_buttons(context, chat_id):
    keyboard = [
        [InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{SUB_CHANNEL_1}")],
        [InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{SUB_CHANNEL_2}")],
        [InlineKeyboardButton("Try Again", callback_data='try_again')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id, "You must subscribe to the following channels to access the files:", reply_markup=reply_markup)

@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='OK')

def main() -> None:
    updater = Updater(TELEGRAM_TOKEN)

    # Register handlers
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(Command Here's the continuation and completion of the updated `bot.py` code:

```python
    updater.dispatcher.add_handler(CommandHandler('upload', upload_file))
    updater.dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
    updater.dispatcher.add_handler(CommandHandler('retrieve', handle_retrieve_file))

    # Start polling for updates
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    # Start both Flask and the Telegram bot in the same process
    Thread(target=main).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
