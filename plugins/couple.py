from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Couple command by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    partner = await db.get_random_couple(user_id)
    if not partner:
        await update.message.reply_text("Not enough users or you're on cooldown (10 minutes). Try again later.")
        return

    message = (
        f"{update.effective_user.full_name} သည် {partner['name']} သင်နဲ့ဖူးစာဖက်ပါ 💙\n"
        "ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့\n"
        "(10 မိနစ်တစ်ခါ auto ရွေးပေးတာပါ)"
    )
    await update.message.reply_text(message)
    logger.info(f"Matched {user_id} with {partner['user_id']} for couple command")

def register_handlers(application):
    logger.info("Registering couple handlers")
    application.add_handler(CommandHandler("couple", couple))