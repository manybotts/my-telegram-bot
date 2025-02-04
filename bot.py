import logging
import os
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))
DUMP_CHANNEL = os.getenv('DUMP_CHANNEL')
FORCE_CHANNELS = list(map(str, os.getenv('FORCE_CHANNELS', '').split(',')))

# MongoDB connection
mongo_uri = os.getenv('MONGO_URI')  # Your MongoDB URI
client = MongoClient(mongo_uri)
db = client['telegram_bot_db']  # Your database name
users_collection = db['users']  # Collection for user data
files_collection = db['files']  # Collection for files data

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Register or update user in the database
    users_collection.update_one({'user_id': user_id}, {'$set': {'username': user_name}}, upsert=True)

    await update.message.reply_text(f'Hello {user_name}! Welcome to the bot.')

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You do not have permission to upload files.")
        return
    
    if update.message.document:
        document = update.message.document
        file_id = document.file_id
        file_name = document.file_name

        # Send the file to the dump channel
        await context.bot.send_document(chat_id=DUMP_CHANNEL, document=document)

        # Store file info in the database
        files_collection.insert_one({
            'file_id': file_id,
            'file_name': file_name,
            'uploaded_by': update.effective_user.id
        })

        # Generate a permanent link here (you may need to implement this)
        link = f"https://your-heroku-app.herokuapp.com/file/{file_id}"  # Example link generation
        await update.message.reply_text(f"File uploaded successfully! Here's the link: {link}")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You do not have permission to broadcast messages.")
        return

    message = " ".join(context.args)
    users = users_collection.find()
    for user in users:
        await context.bot.send_message(chat_id=user['user_id'], text=message)

async def view_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total_users = users_collection.count_documents({})
    total_files = files_collection.count_documents({})
    
    await update.message.reply_text(f"Total Users: {total_users}\nTotal Files Uploaded: {total_files}")

def main():
    application = ApplicationBuilder().token("YOUR_TOKEN").build()  # Replace with your bot token

    # Register handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Document.ALL, upload_file))  # Change Filters to filters
    application.add_handler(CommandHandler('broadcast', broadcast_message))
    application.add_handler(CommandHandler('stats', view_stats))  # Command to show stats

    # Start polling for updates
    application.run_polling()

if __name__ == '__main__':
    main()
