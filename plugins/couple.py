from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import random
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

last_couple_time = None

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_couple_time
    now = datetime.utcnow()
    if last_couple_time and (now - last_couple_time) < timedelta(minutes=10):
        await update.message.reply_text("Wait 10 minutes for the next couple!")
        return

    users = await db.get_all_users()
    if len(users) < 2:
        await update.message.reply_text("Not enough users for a couple.")
        return

    user1, user2 = random.sample(users, 2)
    await update.message.reply_text(
        f"{user1['name']} သည် {user2['name']} သင်နဲ့ဖူးစာဖက်ပါ\n"
        "ရီးစားရှာပေးတာပါ ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့"
    )
    last_couple_time = now

def register_handlers(application: Application):
    application.add_handler(CommandHandler("couple", couple))