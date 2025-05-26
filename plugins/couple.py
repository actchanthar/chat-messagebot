from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Couple command initiated by user {user_id} in chat {chat_id}")

    users = await db.get_all_users()
    if not users or len(users) < 2:
        await update.message.reply_text("Not enough users to find a couple!")
        logger.info(f"Not enough users for couple command by user {user_id}")
        return

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        logger.error(f"User {user_id} not found")
        return

    other_users = [u for u in users if u["user_id"] != user_id]
    partner = random.choice(other_users)
    user_mention = f"@{user['name']}" if user.get("username") else user["name"]
    partner_mention = f"@{partner['name']}" if partner.get("username") else partner["name"]

    message = (
        f"{user_mention} သူသည် {partner_mention} သင်နဲ့ဖူးစာဖက်ပါ ရီးစားရှာပေးတာပါ\n"
        "ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့"
    )
    await update.message.reply_text(message, parse_mode="HTML")
    logger.info(f"Matched user {user_id} with {partner['user_id']} for couple command")

def register_handlers(application: Application):
    logger.info("Registering couple handlers")
    application.add_handler(CommandHandler("couple", couple))