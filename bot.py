import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler
from telegram.ext import filters
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
DUMP_CHANNEL_ID = os.getenv("DUMP_CHANNEL_ID")  # ID or username of the dump channel
ADMINS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS").split(',')]

# Initialize Flask app
app = Flask(__name__)

# Start command handler
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    update.message.reply_text(
        f'Hello, {user.first_name}! Welcome to the file management bot. Use /help to see available commands.',
    )

# Help command handler
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text('Available commands:\n/start - Start the bot\n/help - Show help\n/upload - Upload a file (admins only)')

# Command to upload files (limited to admins)
def upload_file(update: Update, context: CallbackContext):
    if update.message.from_user.id in ADMINS:
        update.message.reply_text("Please send me the file you'd like to upload.")
    else:
        update.message.reply_text("You are not authorized to upload files.")

# Handle incoming documents (for admin file uploads)
def handle_document(update: Update, context: CallbackContext):
    if update.message.from_user.id in ADMINS:
        file = update.message.document.get_file()
        new_file = context.bot.send_document(chat_id=DUMP_CHANNEL_ID, document=file)
        files_collection.insert_one({
            'file_name': update.message.document.file_name,
            'file_id': new_file.document.file_id,
            'user_id': update.message.from_user.id
        })
        
        update.message.reply_text(f"File '{update.message.document.file_name}' uploaded to the dump channel.")
    else:
        update.message.reply_text("You are not authorized to upload files.")

# Health check route
@app.route('/health', methods=['GET'])
def health():
    return jsonify(status='OK')

def main() -> None:
    # Setup the bot
    updater = Updater(TELEGRAM_TOKEN)

    # Register handlers
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(CommandHandler('upload', upload_file))
    updater.dispatcher.add_handler(MessageHandler(filters.Document(), handle_document))

    # Start polling for updates
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    # Start both Flask and the Telegram bot in the same process
    Thread(target=main).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
