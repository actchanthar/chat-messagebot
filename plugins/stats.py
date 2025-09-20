from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show comprehensive user statistics"""
    user_id = str(update.effective_user.id)
    
    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("User not found. Please start with /start.")
            return

        balance = user.get('balance', 0)
        messages = user.get('messages', 0)
        total_withdrawn = user.get('total_withdrawn', 0)
        referrals = user.get('successful_referrals', 0)
        user_level = user.get('user_level', 1)
        total_earnings = user.get('total_earnings', 0)
        
        stats_message = f"""
📊 **Your Statistics**

💰 **Balance:** {int(balance)} {CURRENCY}
📝 **Messages:** {messages:,}
🎯 **Level:** {user_level}
💸 **Total Earned:** {int(total_earnings)} {CURRENCY}
💵 **Total Withdrawn:** {int(total_withdrawn)} {CURRENCY}
👥 **Referrals:** {referrals}
📈 **Net Earnings:** {int(total_earnings - total_withdrawn)} {CURRENCY}

🎉 Keep chatting to earn more!
        """
        
        await update.message.reply_text(stats_message)
        
    except Exception as e:
        logger.error(f"Error getting stats for user {user_id}: {e}")
        await update.message.reply_text("Error retrieving statistics. Please try again.")

def register_handlers(application: Application):
    """Register stats handlers"""
    application.add_handler(CommandHandler("stats", user_stats))
