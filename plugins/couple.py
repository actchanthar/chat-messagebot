from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    last_couple_time = await db.get_last_couple_time()
    current_time = datetime.utcnow()

    if (current_time - last_couple_time).total_seconds() < 600:  # 10 minutes
        remaining = 600 - int((current_time - last_couple_time).total_seconds())
        await update.message.reply_text(f"Please wait {remaining // 60} minutes and {remaining % 60} seconds for the next couple!")
        return

    users = await db.get_random_users(count=2)
    if len(users) < 2:
        await update.message.reply_text("Not enough users to form a couple!")
        return

    user1, user2 = users
    mention1 = f'<a href="tg://user?id={user1["user_id"]}">{user1["name"]}</a>'
    mention2 = f'<a href="tg://user?id={user2["user_id"]}">{user2["name"]}</a>'
    await update.message.reply_text(
        f"{mention1} သူသည် {mention2} သင်နဲ့ဖူးစာဖက်ပါ ရီးစားရှာပေးတာပါ\n"
        "ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့",
        parse_mode="HTML"
    )
    await db.set_last_couple_time(current_time)

def register_handlers(application):
    application.add_handler(CommandHandler("couple", couple))