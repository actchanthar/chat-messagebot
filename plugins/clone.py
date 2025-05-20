from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from database.database import AsyncIOMotorClient
from config import MONGODB_NAME

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def clone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /clone <new_mongodb_url>")
        return

    new_mongodb_url = context.args[0]
    try:
        new_client = AsyncIOMotorClient(new_mongodb_url)
        new_db = new_client[MONGODB_NAME]
        collections = ["users", "groups", "rewards", "settings", "channels"]
        
        for collection_name in collections:
            old_collection = db.db[collection_name]
            new_collection = new_db[collection_name]
            documents = await old_collection.find().to_list(length=None)
            if documents:
                await new_collection.insert_many(documents)
                logger.info(f"Cloned {len(documents)} documents to {collection_name}")
        
        await update.message.reply_text(f"Database cloned to {new_mongodb_url} successfully.")
    except Exception as e:
        logger.error(f"Error cloning database: {e}")
        await update.message.reply_text("Failed to clone database. Check the MongoDB URL.")

def register_handlers(application: Application):
    logger.info("Registering clone handlers")
    application.add_handler(CommandHandler("clone", clone))