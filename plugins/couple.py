from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from random import sample
from datetime import datetime, timedelta
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    last_couple_time = await db.get_setting("last_couple_time", datetime.min)
    if datetime.utcnow() < last_couple_time + timedelta(minutes=10):
        await update.message.reply_text("Couple selection is on cooldown. Try again later.")
        return

    users = await db.get_all_users()
    if len(users) < 2:
        await update.message.reply_text("Not enough users to select a couple.")
        return

    couple_users = sample(users, 2)
    user1, user2 = couple_users
    message = (
        f"{user1['name']} သူသည် {user2['name']} သင်နဲ့ဖူးစာဖက်ပါ ရီးစားရှာ‌ ပေးတာပါ\n"
        "ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့ 💙"
    )
    await update.message.reply_text(message)
    await db.set_setting("last_couple_time", datetime.utcnow())

def register_handlers(application: Application):
    logger.info("Registering couple handlers")
    application.add_handler(CommandHandler("couple", couple))