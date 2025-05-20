from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import random
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

last_couple_time = None

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    global last_couple_time

    if last_couple_time and (datetime.utcnow() - last_couple_time) < timedelta(minutes=10):
        await update.message.reply_text("Please wait 10 minutes before using /couple again.")
        return

    users = await db.get_all_users()
    if len(users) < 2:
        await update.message.reply_text("Not enough users to form a couple!")
        return

    user1, user2 = random.sample(users, 2)
    await update.message.reply_text(
        f"{user1['name']} mention သူသည်  {user2['name']} mention သင်နဲ့ဖူးစာဖက်ပါ ရီးစားရှာ‌ ပေးတာပါ\n"
        "ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့"
    )
    last_couple_time = datetime.utcnow()

def register_handlers(application: Application):
    logger.info("Registering couple handlers")
    application.add_handler(CommandHandler("couple", couple))